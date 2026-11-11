"""Build the project's evidence documents from the loaded data: every number is computed at build time.

Outputs are Markdown strings; ``scripts/build_reports.py`` writes them to ``docs/`` and ``artifacts/``.
"""
from __future__ import annotations

import platform
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd

from src.analytics import descriptive as desc
from src.config import FEATURE_VERSION, PARSER_VERSION, SCHEMA_VERSION
from src.data.provenance import ATTRIBUTION_REQUIREMENT, SOURCE_TERMS_URL, STATSBOMB_ATTRIBUTION
from src.data.schemas import ANALYTICAL_TABLES, TABLE_CONTRACTS, check_contracts
from src.data.validators import dq_profile
from src.features.player_features import metric_dictionary
from src.reporting import insight_cards
from src.visualization import registry

DERIVED_METRICS = [
    ("per-90 rate", "count or value / minutes played × 90", "minutes reconstructed from events",
     "null below the minimum-minutes threshold; never computed for zero minutes"),
    ("role percentile", "percentile rank of a per-90 value within the player's role (or role family) group",
     "eligible players of the same role group", "group size is reported; groups under the minimum fall back to the "
                                                "role family and are flagged"),
    ("possession_proxy_pct", "team passes / (team passes + opponent passes) × 100", "pass attempts of both teams",
     "a pass-share proxy, not timed possession"),
    ("field_tilt_pct", "team final-third touches / both teams' final-third touches × 100", "touches with x ≥ 80",
     "territory proxy from on-ball events"),
    ("ppda", "opponent passes with x ≤ 72 / team tackles + interceptions + fouls + failed challenges with x ≥ 48",
     "defensive actions in the opponent's build-up zone", "lower = more defensive actions per opponent pass; an "
                                                          "event proxy, not pressing quality"),
    ("xg_diff", "sum of StatsBomb xG for − against in a match", "—", "xG is the provider's model output"),
    ("expected points (xPts)", "mean points over 5,000 simulations in which every shot scores with probability "
                               "equal to its xG", "per match", "assumes independent shots; ignores game state"),
    ("progressive pass", "completed pass starting at x ≥ 48 that ends at least 25% closer to the goal centre",
     "—", "project definition; other providers use different thresholds"),
    ("progressive carry", "carry ending at least 25% closer to the goal centre, ending at x ≥ 48 and gaining ≥ 5 "
                          "units", "—", "project definition"),
    ("Expected Threat (xT)", "fixed point of xT(c) = P(shot|c)·value(shot|c) + P(move|c)·Σ T(c→c')·xT(c') on a "
                             "16 × 12 grid", "passes + carries (moves), shots", "project-computed and fitted "
                             "in-sample on the analysed matches; shot value = mean StatsBomb xG per cell"),
    ("role fit", "weighted mean of the role's metric percentiles (weights in config.ROLE_METRIC_WEIGHTS)",
     "weights actually available", "transparent heuristic; completeness of the weight set is reported"),
    ("starting-XI slot score", "(0.40 role fit + 0.20 recent form + 0.15 sample reliability + 0.15 workload "
                               "suitability + 0.10 lineup continuity) × position compatibility", "0–100 components",
     "heuristic; 'best' only under these weights and constraints"),
    ("substitute candidate score", "0.35 role compatibility + 0.35 intent fit + 0.15 recent form + 0.15 sample "
                                   "reliability", "bench players not yet used", "no fitness or injury information "
                                                                               "exists in the source"),
    ("minutes-based exposure", "minutes played in the previous 7 / 14 / 28 days in the analysed matches", "—",
     "league minutes only; NOT physical load or fatigue"),
    ("Cliff's delta", "P(a > b) − P(a < b), from the Mann–Whitney U", "two independent samples",
     "|δ| < 0.147 negligible, < 0.33 small, < 0.474 medium, otherwise large"),
    ("epsilon squared", "(H − k + 1) / (n − k) from the Kruskal–Wallis H", "k groups, n observations",
     "< 0.08 small, < 0.26 medium, otherwise large"),
]


def _md(df: pd.DataFrame, max_rows: int | None = None, floatfmt: str = "{:.3f}") -> str:
    """DataFrame to a GitHub Markdown table (no optional dependency)."""
    if df is None or len(df) == 0:
        return "_no rows_\n"
    d = df.head(max_rows) if max_rows else df

    def cell(v: Any) -> str:
        if isinstance(v, float):
            return "" if np.isnan(v) else (floatfmt.format(v) if abs(v) < 1e6 else f"{v:,.0f}")
        if isinstance(v, (pd.Timestamp, datetime)):
            return v.strftime("%Y-%m-%d")
        return str(v).replace("|", "\\|").replace("\n", " ")

    head = "| " + " | ".join(str(c) for c in d.columns) + " |\n| " + " | ".join("---" for _ in d.columns) + " |\n"
    body = "".join("| " + " | ".join(cell(v) for v in row) + " |\n" for row in d.itertuples(index=False))
    more = f"\n_{len(df) - len(d)} more rows not shown._\n" if max_rows and len(df) > max_rows else ""
    return head + body + more


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def environment() -> dict[str, str]:
    """Versions of the packages actually imported in this environment."""
    import importlib

    out = {"python": platform.python_version(), "platform": platform.platform()}
    for pkg in ("pandas", "numpy", "scipy", "sklearn", "plotly", "matplotlib", "seaborn", "networkx", "streamlit",
                "mplsoccer", "shap", "pyarrow", "nbconvert", "pytest"):
        try:
            out[pkg] = importlib.import_module(pkg).__version__
        except Exception:
            out[pkg] = "not installed"
    return out


def results_snapshot(ws: Any, include_slow: bool = True) -> dict[str, Any]:
    """Key results of the current run as a flat dictionary (also written to artifacts/tables/results.json)."""
    b, team = ws.bundle, ws.focus
    k = desc.season_kpis(b, team)
    xp = ws.xpts()
    xp = xp[xp["team_name"] == team]
    sq = ws.squad(team).set_index("player_name")
    conc = desc.concentration(sq["xg"] + sq["xa"])
    q = b.quality
    out: dict[str, Any] = {
        "generated_utc": _stamp(), "focus_team": team, "synthetic": ws.synthetic,
        "matches": k["matches"], "events": int(len(b.tables["events"])),
        "players_in_squads": int(b.tables["appearances"]["player_id"].nunique()),
        "teams": int(b.team_stats["team_name"].nunique()),
        "raw_files": int(len(b.manifest)) if b.manifest is not None else 0,
        "raw_mb": round(float(b.manifest["bytes"].sum()) / 1e6, 2) if b.manifest is not None else None,
        "quality_checks": f"{int((q['status'] == 'PASS').sum())}/{len(q)}",
        "wins": k["wins"], "draws": k["draws"], "losses": k["losses"], "points": k["points"],
        "xpts": round(float(xp["xpts"].sum()), 1), "goals_for": k["goals_for"], "goals_against": k["goals_against"],
        "xg_for": round(k["xg_for"], 1), "xg_against": round(k["xg_against"], 1),
        "top3_chance_share": round(float(conc["share"].head(3).sum()), 3) if len(conc) >= 3 else None,
    }
    cs = ws.centrality_summary(team)
    if len(cs):
        out["hub_pagerank"] = str(cs.iloc[-1]["player"])
        out["hub_betweenness"] = str(cs.sort_values("betweenness").iloc[-1]["player"])
    corr = ws.correlations(team)
    if len(corr):
        top = corr.iloc[0]
        out["corr_significant_after_fdr"] = int((corr["spearman_q_BH"] < 0.05).sum())
        out["corr_top"] = {"variable": top["variable"], "rho": round(float(top["spearman_rho"]), 3),
                           "ci": [round(float(top["rho_ci_low"]), 3), round(float(top["rho_ci_high"]), 3)],
                           "q": round(float(top["spearman_q_BH"]), 3), "n": int(top["n"])}
    for t in ws.group_tests(team):
        if t["comparison"] == "home vs away":
            out["venue"] = {"delta": round(float(t["effect_size"]), 3), "p": round(float(t["p_value"]), 3),
                            "mean_diff": round(float(t["mean_diff"]), 2)}
    g = ws.xt_grid()
    if g is not None:
        out["xt"] = {"grid": f"{g.nx}x{g.ny}", "moves": g.n_moves, "shots": g.n_shots, "iterations": g.iterations,
                     "converged": bool(g.converged), "max_value": round(float(g.grid.max()), 3)}
    if include_slow:
        pca, cl = ws.pca(), ws.clusters()
        if pca:
            out["pca"] = {"pc1": round(float(pca["explained"][0]), 3), "pc2": round(float(pca["explained"][1]), 3),
                          "components_for_80pct": pca["components_for_80pct"], "players": pca["n_players"]}
        if cl:
            out["clustering"] = {"k_best": cl["k_best"], "silhouette": round(cl["silhouette_best"], 3),
                                 "k_bic": cl["k_bic"], "dbscan_noise": cl["dbscan_noise"],
                                 "dbscan_clusters": cl["dbscan_clusters"]}
        res = ws.models(team)
        out["model_fitted"] = bool(res.get("fitted"))
        if res.get("fitted"):
            cv = res["cv_summary"]
            out["cv_f1"] = {m: round(float(v), 3) for m, v in cv[("f1", "mean")].items()}
            out["cv_auc"] = {m: round(float(v), 3) for m, v in cv[("roc_auc", "mean")].dropna().items()}
            out["best_model"] = res["best"]
            hold = res["holdout"].set_index("model")
            out["holdout_auc"] = round(float(hold.loc[res["best"], "roc_auc"]), 3)
            out["holdout_brier"] = round(float(hold.loc[res["best"], "brier"]), 3)
            out["model_rows"], out["model_matches"] = res["gate"]["rows"], res["gate"]["matches"]
        ag = ws.xi_agreement(team)
        if len(ag):
            out["xi_agreement_mean_pct"] = round(float(ag["agreement_pct"].mean()), 1)
            out["xi_agreement_matches"] = int(len(ag))
        sa = ws.sub_agreement(team)
        if len(sa):
            out["sub_top3_share"] = round(float(sa["on_in_top_k"].mean()), 3)
            out["sub_backtest_n"] = int(len(sa))
            out["sub_random_top3"] = round(float((3 / sa["bench_size"].clip(lower=3)).mean()), 3)
    return out


def catalogue_markdown(ws: Any, table: pd.DataFrame | None = None) -> str:
    """docs/VISUALIZATION_CATALOGUE.md: every chart with its status for the loaded data."""
    table = table if table is not None else registry.status_table(ws, validate=True)
    counts = registry.status_counts(table)
    m = ws.tables["matches"]
    lines = [
        "# Visualization Catalogue", "",
        f"> Generated {_stamp()} by `scripts/build_reports.py` from `src/visualization/catalogue.py` "
        f"(registry schema {registry.REGISTRY_SCHEMA_VERSION}). Status is evaluated against the data loaded for "
        f"this run: **{m['competition_name'].iloc[0]} {m['season_name'].iloc[0]}, {len(m)} matches, focus team "
        f"{ws.focus}**" + (" — SYNTHETIC DEMO DATA." if ws.synthetic else "."),
        "",
        "Every implemented renderer was executed once with default selections while this file was built; a "
        "renderer that raised would be listed as `failed_validation`.", "",
        "## Status summary", "",
        "| status | charts | meaning |", "| --- | --- | --- |",
        f"| `implemented_and_available` | {counts[registry.IMPLEMENTED_AVAILABLE]} | renderer exists, prerequisites "
        f"met, rendered without error |",
        f"| `implemented_but_unavailable` | {counts[registry.IMPLEMENTED_UNAVAILABLE]} | renderer exists but the "
        f"loaded data or an optional package does not support it |",
        f"| `not_implemented` | {counts[registry.NOT_IMPLEMENTED]} | catalogue concept with no renderer; reason "
        f"stated |",
        f"| `failed_validation` | {counts[registry.FAILED_VALIDATION]} | renderer raised during validation |",
        f"| **total** | **{len(table)}** | |", "",
        "The catalogue is open-ended: these counts describe what exists and rendered in this run, not every "
        "possible football chart.", "",
        "## By family", "",
        _md(table.pivot_table(index="category", columns="status", values="chart_id", aggfunc="count", fill_value=0)
            .reset_index()), "",
        "## Entries that are not available", "",
        _md(table[table["status"] != registry.IMPLEMENTED_AVAILABLE][["chart_id", "name", "status", "reason"]]), "",
    ]
    legacy = table[table["legacy_artifact"] != ""][["legacy_artifact", "chart_id", "name"]].sort_values(
        "legacy_artifact")
    lines += ["## Existing gallery artefacts mapped to registry IDs", "",
              "The 27 static figures and 6 HTML dashboards produced by the preserved enhanced notebook "
              "(`visualization_gallery/`) correspond to these registry entries (closest equivalent renderer):", "",
              _md(legacy), ""]
    for cat, g in table.groupby("category", sort=False):
        lines += [f"## {cat}", ""]
        for r in g.itertuples():
            lines += [f"### {r.chart_id} · {r.name}", "",
                      f"- **Question.** {r.research_question}",
                      f"- **Status.** `{r.status}`" + (f" — {r.reason}" if r.reason else ""),
                      f"- **Library / modality / cost.** {r.library} · {r.data_modality} · {r.estimated_cost}"]
            if r.required_columns:
                lines.append(f"- **Requires.** {r.required_columns}"
                             + (f" · at least {r.minimum_matches} matches" if r.minimum_matches > 1 else "")
                             + (f" · at least {r.minimum_players} eligible players" if r.minimum_players else ""))
            if r.params:
                lines.append(f"- **Selectors.** {r.params}")
            if r.methodology_note:
                lines.append(f"- **Method.** {r.methodology_note}")
            if r.caveat:
                lines.append(f"- **Caveat.** {r.caveat}")
            if r.test_name:
                lines.append(f"- **Test.** `{r.test_name}[{r.chart_id}]`")
            lines.append("")
    return "\n".join(lines)


def data_dictionary_markdown(ws: Any) -> str:
    """docs/DATA_DICTIONARY.md: tables, fields (measured types and missingness) and metric definitions."""
    b = ws.bundle
    contracts = check_contracts(b)
    lines = ["# Data Dictionary", "",
             f"> Generated {_stamp()} from the loaded data (schema {SCHEMA_VERSION}, parser {PARSER_VERSION}, "
             f"features {FEATURE_VERSION}). Types, missingness and distinct counts are measured, not assumed.", "",
             "## Tables and contracts", "",
             _md(contracts.assign(key=[", ".join(TABLE_CONTRACTS[t].key) for t in contracts["table"]],
                                  description=[TABLE_CONTRACTS[t].description for t in contracts["table"]])
                 [["table", "origin", "rows", "grain", "key", "status", "description"]]), "",
             "`origin = source` means the fields are parsed from StatsBomb files; `derived` means computed by this "
             "project from those fields.", "",
             "## Metric definitions (player and team counts)", "", _md(metric_dictionary()), "",
             "## Derived metrics and scores", "",
             _md(pd.DataFrame(DERIVED_METRICS, columns=["metric", "formula", "denominator / inputs",
                                                        "interpretation and caveat"])), ""]
    order = ["matches", "managers", "squads", "events", "appearances", "spells", "goals", "formations",
             "substitutions_raw", "sending_offs", "period_bounds"] + ANALYTICAL_TABLES
    for name in order:
        df = b.table(name) if name in ANALYTICAL_TABLES else b.tables.get(name)
        if not isinstance(df, pd.DataFrame) or df.shape[1] == 0:
            continue
        origin = TABLE_CONTRACTS[name].origin if name in TABLE_CONTRACTS else "derived"
        lines += [f"## Table `{name}` — {len(df):,} rows ({origin})", "",
                  _md(dq_profile(df, name)[["column", "dtype", "missing_pct", "distinct"]], floatfmt="{:.1f}"), ""]
    return "\n".join(lines)


def provenance_markdown(manifest: dict[str, Any]) -> str:
    """docs/DATA_PROVENANCE.md from the machine-readable manifest."""
    s, sc, r, v = manifest["source"], manifest["scope"], manifest["retrieval"], manifest["validation"]
    rev = s["revision_at_verification"]
    files = pd.DataFrame(manifest["files"])
    by = files.groupby("resource").agg(files=("path", "size"), bytes=("bytes", "sum")).reset_index() \
        if len(files) else pd.DataFrame()
    lines = ["# Data Provenance", "",
             f"> Generated {_stamp()} from `data/manifest/source_manifest.json` (manifest version "
             f"{manifest['manifest_version']}). The manifest stores hashes, sizes and counts only; no source data is "
             f"redistributed in this repository.", "",
             "## Source", "",
             f"- **Name.** {s['name']}", f"- **Publisher.** {s['publisher']}",
             f"- **Repository.** {s['repository']}", f"- **Download base URL.** `{s['base_url']}`",
             f"- **Terms.** {s['terms_url']}", f"- **Field documentation.** {s['documentation_url']}",
             f"- **Attribution requirement.** {s['attribution_requirement']}",
             f"- **Source revision when verified.** commit `{rev.get('commit_sha') or 'not available'}` "
             f"({rev.get('commit_date') or rev.get('status')})", "",
             "### Terms as read from the source licence", ""]
    lines += [f"- {t}" for t in s["terms_summary"]]
    lines += ["", "Consequence for this project: raw and processed event tables are **not** committed. The pipeline "
                  "downloads the files from the official repository on first run and caches them locally "
                  "(`data/raw/`, git-ignored). Figures, summary tables and reports are analysis and carry the "
                  "attribution.", "",
              "## Scope", "",
              f"- **Competition / season.** {sc['competition_name']} {sc['season_name']} (competition "
              f"{sc['competition_id']}, season {sc['season_id']})",
              f"- **Matches.** {sc['matches_analysed']} analysed of {sc['matches_published_for_season']} published "
              f"for this competition-season; focus team filter: {sc['focus_team']}",
              f"- **Dates.** {sc['first_match_date']} to {sc['last_match_date']}",
              f"- **Match IDs.** {', '.join(str(i) for i in sc['match_ids'])}", "",
              "## Retrieval", "",
              f"- **Files.** {r['files']} ({r['bytes'] / 1e6:.2f} MB), {r['failed_files']} failed",
              f"- **Raw files written between.** {r['earliest_file_written_utc']} and "
              f"{r['latest_file_written_utc']} (UTC; cache hits keep their original download time)",
              f"- **Integrity.** SHA-256 of every file is in the manifest", "",
              _md(by), "",
              "## Parsed tables", "",
              _md(pd.DataFrame([{"table": k, **val} for k, val in manifest["tables"].items()])), "",
              "## Validation", "",
              f"- Domain rules passed: **{v['rules_passed']} / {v['rules_total']}**",
              f"- Table contracts passed: **{v['contracts_passed']} / {v['contracts_total']}**", "",
              _md(pd.DataFrame(v["rules"])), "",
              "## Transformations", ""]
    lines += [f"{i}. {t}" for i, t in enumerate(manifest["transformations"], 1)]
    lines += ["", "## Derived-table dependencies", "",
              _md(pd.DataFrame([{"table": k, "built from": ", ".join(d)}
                                for k, d in manifest["derived_table_dependencies"].items()])), "",
              "## Data limitations", ""]
    lines += [f"- {t}" for t in manifest["data_limitations"]]
    lines += ["", "## First files in the manifest (illustration)", "",
              _md(files[["path", "bytes", "sha256", "file_written_utc"]].head(6)) if len(files) else "", ""]
    return "\n".join(lines)


def analysis_report_markdown(ws: Any, snap: dict[str, Any], cards: list[dict[str, str]],
                             counts: dict[str, int]) -> str:
    """artifacts/reports/ANALYSIS_REPORT_V3.md: the written report, generated from the current run."""
    b, team = ws.bundle, ws.focus
    m = b.tables["matches"]
    tm = ws.team_matches(team)
    corr = ws.correlations(team)
    tests = ws.group_tests(team)
    env = environment()
    lines = [f"# Analysis Report (V3) — Football Managerial Decision Analytics", "",
             f"> Generated {snap['generated_utc']} by `scripts/build_reports.py`. Every number below is computed "
             f"from the data loaded in that run; chart IDs refer to `docs/VISUALIZATION_CATALOGUE.md`.", "",
             "## 1. Executive summary", "",
             f"{team} played {snap['matches']} analysed matches ({snap['wins']} wins, {snap['draws']} draws, "
             f"{snap['losses']} losses): {snap['points']:.0f} points against {snap['xpts']} shot-based expected "
             f"points, {snap['goals_for']} goals from {snap['xg_for']} xG, {snap['goals_against']} conceded from "
             f"{snap['xg_against']} xG against. The findings are descriptive associations in one team-season and "
             f"are presented with their uncertainty.", "",
             "## 2. Research question and scope", "",
             "How can event, lineup and match-state data be turned into transparent evidence that supports "
             "starting-XI selection, role fit, tactical interpretation, substitution choices and the review of "
             "observable managerial decisions?", "",
             f"- **Data.** {STATSBOMB_ATTRIBUTION}",
             f"- **Scope.** {m['competition_name'].iloc[0]} {m['season_name'].iloc[0]}; {len(m)} matches "
             f"({m['match_date'].min():%d %b %Y} – {m['match_date'].max():%d %b %Y}); {snap['events']:,} events; "
             f"{snap['players_in_squads']} players in match-day squads; {snap['teams']} teams.",
             f"- **Sample caveat.** Every analysed match involves {team}; opponents appear twice (home and away).", "",
             "## 3. Data quality", "",
             f"- Domain rules passed: {snap['quality_checks']}; table contracts: "
             f"{int((check_contracts(b)['status'] == 'PASS').sum())}/{len(TABLE_CONTRACTS)}.",
             f"- Raw files: {snap['raw_files']} ({snap['raw_mb']} MB), each with a SHA-256 hash in the manifest.",
             "- Missing values are structural (qualifiers exist only for their event type); nothing is imputed.",
             "- One published 360 file was found whose frame identifiers do not match its event file; 360 frames "
             "are optional and are shown only when they can be joined to events.", "",
             "## 4. Team performance", "",
             _md(pd.DataFrame([
                 ("Points per match", f"{tm['points'].mean():.2f}"),
                 ("xG difference per match", f"{tm['xg_diff'].mean():+.2f}"),
                 ("Possession proxy (pass share)", f"{tm['possession_proxy_pct'].mean():.1f}%"),
                 ("Field tilt", f"{tm['field_tilt_pct'].mean():.1f}%"),
                 ("Pass completion", f"{tm['pass_completion_pct'].mean():.1f}%"),
                 ("PPDA (median)", f"{tm['ppda'].median():.1f}"),
                 ("Top-three share of xG + xA", f"{snap['top3_chance_share']:.0%}" if snap.get("top3_chance_share")
                  else "n/a"),
             ], columns=["indicator", "value"])), ""]
    if len(corr):
        lines += ["## 5. Statistical inference", "",
                  f"Spearman correlation of {len(corr)} match variables with goal difference (n = "
                  f"{int(corr['n'].iloc[0])} matches, 2,000 bootstrap resamples, Benjamini–Hochberg):", "",
                  _md(corr[["variable", "n", "pearson_r", "spearman_rho", "rho_ci_low", "rho_ci_high", "kendall_tau",
                            "spearman_p", "spearman_q_BH"]]), "",
                  f"{snap.get('corr_significant_after_fdr', 0)} of {len(corr)} variables have q < 0.05. "
                  f"With n = {int(corr['n'].iloc[0])}, only |r| of roughly "
                  f"{float(__import__('src.analytics.statistical_tests', fromlist=['x']).min_detectable_correlation(int(corr['n'].iloc[0]))):.2f} "
                  f"or more is detectable with 80% power (chart J-214).", ""]
    if tests:
        lines += ["Group comparisons (Mann–Whitney U, Cliff's δ, bootstrap CI of the mean difference):", "",
                  _md(pd.DataFrame(tests)[["comparison", "n_a", "n_b", "mean_a", "mean_b", "mean_diff",
                                           "diff_ci_low", "diff_ci_high", "p_value", "effect_size", "magnitude"]]),
                  ""]
    lines += ["## 6. Models and unsupervised structure", ""]
    if snap.get("model_fitted"):
        lines += [f"Target: start selection (does a match-day squad member start?). {snap['model_rows']} rows from "
                  f"{snap['model_matches']} matches; expanding-window cross-validation split by match.", "",
                  _md(pd.DataFrame({"model": list(snap["cv_f1"]), "cv_f1": list(snap["cv_f1"].values()),
                                    "cv_roc_auc": [snap["cv_auc"].get(k, np.nan) for k in snap["cv_f1"]]})), "",
                  f"Best on the chronological hold-out: {snap['best_model']} (ROC-AUC {snap['holdout_auc']}, Brier "
                  f"{snap['holdout_brier']}). Match-result, goals, injury and market-value models are **not** "
                  f"fitted: the data do not support them (see the Model Evaluation page).", ""]
    else:
        lines += ["No supervised model was fitted: the sample gate was not met.", ""]
    if snap.get("clustering"):
        c, p = snap["clustering"], snap.get("pca", {})
        lines += [f"Player profiles: PC1 {p.get('pc1', 0):.0%}, PC2 {p.get('pc2', 0):.0%} of variance "
                  f"({p.get('players')} players, {p.get('components_for_80pct')} components for 80%). Clustering: "
                  f"silhouette-best k = {c['k_best']} ({c['silhouette']}), BIC prefers k = {c['k_bic']}, DBSCAN "
                  f"finds {c['dbscan_clusters']} dense group(s) and {c['dbscan_noise']} outlying players — profiles "
                  f"form a continuum.", ""]
    if snap.get("xt"):
        x = snap["xt"]
        lines += [f"Expected Threat (project-computed): {x['grid']} grid fitted on {x['moves']:,} passes and "
                  f"carries and {x['shots']:,} shots; value iteration "
                  f"{'converged' if x['converged'] else 'did NOT converge'} in {x['iterations']} iterations; "
                  f"maximum cell value {x['max_value']}. In-sample and descriptive.", ""]
    lines += ["## 7. Decision support", ""]
    if snap.get("xi_agreement_mean_pct") is not None:
        lines.append(f"- **Starting XI.** The pre-match shortlist shares {snap['xi_agreement_mean_pct']}% of the "
                     f"actual XI on average over {snap['xi_agreement_matches']} matches. This is similarity to the "
                     f"manager's choice, not evidence that either was better.")
    if snap.get("sub_top3_share") is not None:
        lines.append(f"- **Substitutions.** The heuristic's top three contains the player who actually came on in "
                     f"{snap['sub_top3_share']:.1%} of {snap['sub_backtest_n']} non-injury substitutions (a random "
                     f"pick of three from the bench: about {snap['sub_random_top3']:.0%}).")
    lines += ["- Both tools are transparent heuristics with stated weights and constraints; no injury or fitness "
              "information exists in the source, so availability must be supplied by the analyst.", "",
              "## 8. Managerial evidence cards", "", insight_cards.cards_markdown(cards),
              "## 9. Visualization inventory", "",
              f"- implemented and available: **{counts[registry.IMPLEMENTED_AVAILABLE]}**",
              f"- implemented but unavailable: **{counts[registry.IMPLEMENTED_UNAVAILABLE]}**",
              f"- not implemented (reason stated): **{counts[registry.NOT_IMPLEMENTED]}**",
              f"- failed validation: **{counts[registry.FAILED_VALIDATION]}**", "",
              "## 10. Limitations", "",
              "Team-centric sample; league matches only; no injury, fitness, tracking, age or market data; xG, xPts "
              "and xT are model outputs; 34 matches limit statistical power; every relationship is an association, "
              "not a causal effect; heuristic scores are 'best' only under their stated weights.", "",
              "## 11. Reproducibility", "",
              _md(pd.DataFrame(list(env.items()), columns=["component", "version"])), "",
              "## 12. Attribution", "", f"{STATSBOMB_ATTRIBUTION} {ATTRIBUTION_REQUIREMENT} Terms: {SOURCE_TERMS_URL}",
              ""]
    return "\n".join(lines)
