"""Explainable starting-XI decision support.

Method: every (player, formation slot) pair receives a transparent weighted score
from season-to-date role fit, recent form, sample reliability, a workload proxy
and lineup continuity, multiplied by a position-compatibility factor. The XI is
the assignment of distinct players to the 11 slots that maximises the total
score (Hungarian algorithm, ``scipy.optimize.linear_sum_assignment``) — exact,
deterministic for the same inputs, and constrained (one player per slot, no
duplicates, compatibility > 0, unavailable players excluded).

Only information available *before* the decision date is used. The output is a
reproducible analytical recommendation, not a claim to out-know a coach.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment

from .config import Config, ROLE_LABEL, SIDE_MATCH_BONUS, compatibility, position_side
from .features import (add_percentiles, all_metric_columns, player_season_table, recent_form, role_fit_scores,
                       workload_suitability)

INFEASIBLE = 1e6


@dataclass
class DecisionContext:
    """All pre-decision information for one team at one decision date."""
    team_id: Any
    team_name: str
    asof: pd.Timestamp | None
    candidates: pd.DataFrame            # one row per candidate player with role-independent components
    season_pct: pd.DataFrame            # season-to-date table with percentiles (all players, benchmark pool)
    previous_starters: set
    pool_description: str
    notes: list[str] = field(default_factory=list)


@dataclass
class XIResult:
    formation: str
    lineup: pd.DataFrame
    total_score: float
    warnings: list[str]
    omitted: pd.DataFrame
    depth: pd.DataFrame
    score_matrix: pd.DataFrame
    method: str


def workload_asof(appearances: pd.DataFrame, matches: pd.DataFrame, team_id: Any, asof: pd.Timestamp
                  ) -> pd.DataFrame:
    """Minutes in the previous 7/14/28 days and rest days relative to ``asof`` (dataset matches only)."""
    a = appearances[(appearances["team_id"] == team_id) & appearances["appeared"]].merge(
        matches[["match_id", "match_date"]], on="match_id")
    a = a[a["match_date"] < asof]
    rows = []
    for pid, g in a.groupby("player_id"):
        rows.append({"player_id": pid,
                     "minutes_prev_7d": g.loc[g["match_date"] >= asof - pd.Timedelta(days=7), "minutes_played"].sum(),
                     "minutes_prev_14d": g.loc[g["match_date"] >= asof - pd.Timedelta(days=14), "minutes_played"].sum(),
                     "minutes_prev_28d": g.loc[g["match_date"] >= asof - pd.Timedelta(days=28), "minutes_played"].sum(),
                     "rest_days": (asof - g["match_date"].max()).days})
    return pd.DataFrame(rows, columns=["player_id", "minutes_prev_7d", "minutes_prev_14d", "minutes_prev_28d",
                                       "rest_days"])


def decision_context(bundle: Any, team_name: str, match_id: Any = None, asof: pd.Timestamp | None = None,
                     pool: str = "auto", recent_squads: int = 10) -> DecisionContext:
    """Build the pre-decision candidate pool for a team.

    * ``match_id`` given: decision date = that match's date; pool = its matchday squad
      (the announced available players). Stats use only earlier matches.
    * otherwise: hypothetical next fixture ``asof`` (default: 4 days after the last
      analysed match); pool = players in any of the team's last ``recent_squads`` squads.
    """
    cfg: Config = bundle.config
    matches, app, pms = bundle.tables["matches"], bundle.tables["appearances"], bundle.pms
    team_rows = app[app["team_name"] == team_name]
    if team_rows.empty:
        raise ValueError(f"Team {team_name!r} not found in analysed squads")
    team_id = team_rows["team_id"].iloc[0]
    notes: list[str] = []
    if match_id is not None:
        asof = matches.loc[matches["match_id"] == match_id, "match_date"].iloc[0]
        squad_ids = set(app[(app["match_id"] == match_id) & (app["team_id"] == team_id)]["player_id"])
        pool_desc = f"matchday squad of match {match_id} ({asof:%Y-%m-%d})"
    else:
        if asof is None:
            asof = matches["match_date"].max() + pd.Timedelta(days=4)
            notes.append("Hypothetical fixture dated 4 days after the last analysed match.")
        tm = (team_rows.merge(matches[["match_id", "match_date"]], on="match_id")
              .query("match_date < @asof").sort_values("match_date"))
        last_ids = tm["match_id"].drop_duplicates().tail(recent_squads)
        squad_ids = set(tm[tm["match_id"].isin(last_ids)]["player_id"])
        pool_desc = f"players named in the team's last {len(last_ids)} matchday squads before {asof:%Y-%m-%d}"
    season = player_season_table(pms, app, cfg, asof=asof, matches=matches)
    season_pct = add_percentiles(season, all_metric_columns(cfg), cfg)
    form = recent_form(pms, season_pct, cfg, asof=asof)
    wl = workload_asof(app, matches, team_id, asof)
    prev = (app[(app["team_id"] == team_id)].merge(matches[["match_id", "match_date"]], on="match_id")
            .query("match_date < @asof"))
    prev_starters: set = set()
    if not prev.empty:
        last_mid = prev.sort_values("match_date")["match_id"].iloc[-1]
        prev_starters = set(prev[(prev["match_id"] == last_mid) & prev["is_starter"]]["player_id"])
    names = team_rows.drop_duplicates("player_id", keep="last").set_index("player_id")["player_name"]
    cand = pd.DataFrame({"player_id": sorted(squad_ids)})
    cand["player_name"] = cand["player_id"].map(names)
    st = season_pct[season_pct["team_id"] == team_id]
    cand = cand.merge(st[["player_id", "primary_position", "primary_role", "role_family", "minutes_played",
                          "appearances", "starts", "sample_reliability", "coverage_label"]], on="player_id", how="left")
    cand = cand.merge(form[form["team_id"] == team_id][["player_id", "form_score", "form_minutes", "form_apps"]],
                      on="player_id", how="left")
    cand = cand.merge(wl, on="player_id", how="left")
    cand["minutes_played"] = cand["minutes_played"].fillna(0)
    cand["sample_reliability"] = cand["sample_reliability"].fillna(0)
    cand["coverage_label"] = cand["coverage_label"].fillna("no pre-decision minutes")
    cand["workload_suitability"] = workload_suitability(cand["minutes_prev_7d"], cand["rest_days"])
    cand["lineup_continuity"] = np.where(cand["player_id"].isin(prev_starters), 100.0, 0.0)
    if not prev_starters:
        notes.append("No previous match in dataset: continuity component is 0 for all players.")
    # Players whose primary role is unknown (no minutes) fall back to the role seen in squads, flagged.
    unknown_role = cand["primary_role"].isna()
    if unknown_role.any():
        fallback = (app[app["team_id"] == team_id].dropna(subset=["match_role"])
                    .groupby("player_id")["match_role"].agg(lambda s: s.value_counts().index[0]))
        cand.loc[unknown_role, "primary_role"] = cand.loc[unknown_role, "player_id"].map(fallback)
        cand["role_source"] = np.where(unknown_role, "fallback: squad match role (no pre-decision minutes)",
                                       "season primary position (minutes-weighted)")
    else:
        cand["role_source"] = "season primary position (minutes-weighted)"
    return DecisionContext(team_id=team_id, team_name=team_name, asof=asof, candidates=cand, season_pct=season_pct,
                           previous_starters=prev_starters, pool_description=pool_desc, notes=notes)


def score_candidates(ctx: DecisionContext, formation: str, config: Config,
                     unavailable: list | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Long table of component scores per (player, slot) and the slot templates."""
    slots = pd.DataFrame(config.formation_templates[formation])
    unavailable = set(unavailable or [])
    cand = ctx.candidates[~ctx.candidates["player_id"].isin(unavailable)].copy()
    sp = ctx.season_pct[ctx.season_pct["team_id"] == ctx.team_id].set_index("player_id")
    w = config.xi_score_weights
    rows = []
    fits = {}
    for role in slots["role"].unique():
        rf = role_fit_scores(sp.reset_index(), role, config).set_index("player_id")
        fits[role] = rf
    for _, s in slots.iterrows():
        rf = fits[s["role"]]
        for _, c in cand.iterrows():
            pid = c["player_id"]
            comp = compatibility(c["primary_role"], s["role"], config.role_compatibility)
            role_fit = rf["role_fit"].get(pid, np.nan)
            form = c["form_score"] if pd.notna(c["form_score"]) else role_fit
            parts = {"role_fit": role_fit, "recent_form": form, "sample_reliability": c["sample_reliability"],
                     "workload_suitability": c["workload_suitability"], "lineup_continuity": c["lineup_continuity"]}
            base = sum(w[k] * (0.0 if pd.isna(v) else v) for k, v in parts.items())
            side_ok = position_side(c["primary_position"]) == position_side(s["slot"])
            base += SIDE_MATCH_BONUS if side_ok else 0.0
            feasible = comp > 0 and pd.notna(role_fit)
            rows.append({"slot": s["slot"], "slot_role": s["role"], "player_id": pid, "player_name": c["player_name"],
                         "primary_role": c["primary_role"], "compatibility": comp, **parts,
                         "form_fallback": pd.isna(c["form_score"]), "side_match": side_ok,
                         "base_score": base, "score": base * comp if feasible else np.nan, "feasible": feasible,
                         "role_fit_completeness": rf["role_fit_completeness"].get(pid, 0.0),
                         "coverage_label": c["coverage_label"]})
    return pd.DataFrame(rows), slots


def optimize_xi(ctx: DecisionContext, formation: str, config: Config, unavailable: list | None = None,
                forced: dict | None = None) -> XIResult:
    """Constrained optimal assignment of candidates to the formation's 11 slots.

    ``forced`` maps slot -> player_id for what-if analysis (pinned before optimising).
    """
    if formation not in config.formation_templates:
        raise ValueError(f"Unknown formation {formation!r}; options: {list(config.formation_templates)}")
    long, slots = score_candidates(ctx, formation, config, unavailable)
    warnings: list[str] = []
    forced = forced or {}
    if long.empty:
        return XIResult(formation, pd.DataFrame(), 0.0, ["No eligible candidates."], pd.DataFrame(),
                        pd.DataFrame(), long, "n/a")
    players = sorted(long["player_id"].unique())
    slot_ids = list(slots["slot"])
    mat = long.pivot_table(index="player_id", columns="slot", values="score", aggfunc="first").reindex(
        index=players, columns=slot_ids)
    cost = np.where(mat.isna(), INFEASIBLE, -mat.to_numpy(dtype=float))
    for slot, pid in forced.items():
        j = slot_ids.index(slot)
        if pid not in players:
            warnings.append(f"Forced player {pid} is not an eligible candidate; ignored.")
            continue
        i = players.index(pid)
        cost[i, :] = INFEASIBLE
        cost[:, j] = INFEASIBLE
        cost[i, j] = -(mat.iloc[i, j] if pd.notna(mat.iloc[i, j]) else 0.0)
        if pd.isna(mat.iloc[i, j]):
            warnings.append(f"Forced {slot}: player has zero compatibility/score there (manual override).")
    rows_i, cols_j = linear_sum_assignment(cost)
    chosen = []
    for i, j in zip(rows_i, cols_j):
        if cost[i, j] >= INFEASIBLE:
            continue
        chosen.append((players[i], slot_ids[j]))
    filled = {s for _, s in chosen}
    for s in slot_ids:
        if s not in filled:
            warnings.append(f"Insufficient depth: no compatible candidate with pre-decision data for slot {s} — "
                            f"left empty rather than fabricated.")
    lk = long.set_index(["player_id", "slot"])
    lineup = []
    for pid, s in chosen:
        r = lk.loc[(pid, s)]
        lineup.append({"slot": s, "slot_role": r["slot_role"], "player_id": pid, "player_name": r["player_name"],
                       "primary_role": r["primary_role"], "compatibility": r["compatibility"],
                       "role_fit": r["role_fit"], "recent_form": r["recent_form"],
                       "sample_reliability": r["sample_reliability"],
                       "workload_suitability": r["workload_suitability"],
                       "lineup_continuity": r["lineup_continuity"], "score": r["score"] if pd.notna(r["score"]) else 0.0,
                       "form_fallback": r["form_fallback"], "coverage_label": r["coverage_label"],
                       "forced": forced.get(s) == pid})
    order = {s: k for k, s in enumerate(slot_ids)}
    lineup = pd.DataFrame(lineup)
    if not lineup.empty:
        lineup = lineup.sort_values("slot", key=lambda c: c.map(order)).reset_index(drop=True)
        lineup = lineup.merge(slots[["slot", "x", "y"]], on="slot", how="left")
        if (lineup["slot_role"] == "GK").sum() != 1:
            warnings.append("Lineup does not contain exactly one goalkeeper.")
        low = lineup[lineup["coverage_label"].isin(["low data coverage", "no pre-decision minutes"])]
        for _, r in low.iterrows():
            warnings.append(f"{r['player_name']} ({r['slot']}) selected on low data coverage.")
    depth = (long[long["feasible"] & (long["compatibility"] >= 0.8)].groupby(["slot", "slot_role"])["player_id"]
             .nunique().rename("candidates_compat_ge_0.8").reset_index())
    depth = slots[["slot", "role"]].rename(columns={"role": "slot_role"}).merge(depth, on=["slot", "slot_role"],
                                                                                  how="left").fillna(0)
    for _, d in depth.iterrows():
        if d["candidates_compat_ge_0.8"] < 2:
            warnings.append(f"Thin depth at {d['slot']}: {int(d['candidates_compat_ge_0.8'])} natural candidate(s).")
    omitted = explain_omissions(long, lineup, ctx, unavailable or [])
    total = float(lineup["score"].sum()) if not lineup.empty else 0.0
    method = ("Hungarian assignment (scipy linear_sum_assignment) maximising sum of slot scores; "
              f"weights={config.xi_score_weights}; decision date={ctx.asof:%Y-%m-%d}; pool={ctx.pool_description}")
    return XIResult(formation, lineup, total, warnings, omitted, depth, long, method)


def explain_omissions(long: pd.DataFrame, lineup: pd.DataFrame, ctx: DecisionContext,
                      unavailable: list) -> pd.DataFrame:
    """One readable reason per candidate not selected."""
    selected = set(lineup["player_id"]) if not lineup.empty else set()
    by_slot = lineup.set_index("slot") if not lineup.empty else pd.DataFrame()
    rows = []
    comps = ["role_fit", "recent_form", "sample_reliability", "workload_suitability", "lineup_continuity"]
    for _, c in ctx.candidates.iterrows():
        pid = c["player_id"]
        if pid in selected:
            continue
        if pid in set(unavailable):
            reason = "Marked unavailable by user (manual input)."
        else:
            pl = long[(long["player_id"] == pid)]
            feas = pl[pl["feasible"]]
            if pl.empty or feas.empty:
                if c["minutes_played"] <= 0:
                    reason = "No minutes in analysed matches before decision date (insufficient sample)."
                else:
                    reason = f"No compatible slot in this formation for primary role {c['primary_role']}."
            else:
                best = feas.sort_values("score", ascending=False).iloc[0]
                if best["slot"] in by_slot.index:
                    sel = by_slot.loc[best["slot"]]
                    gap = sel["score"] - best["score"]
                    diffs = {k: float(sel[k]) - float(best[k] if pd.notna(best[k]) else 0) for k in comps}
                    key = max(diffs, key=diffs.get)
                    reason = (f"Best slot {best['slot']} (score {best['score']:.1f}); {sel['player_name']} scored "
                              f"{sel['score']:.1f} (+{gap:.1f}); largest gap in {key.replace('_', ' ')}.")
                else:
                    reason = f"Best slot {best['slot']} (score {best['score']:.1f}) filled by assignment trade-off."
                if c["workload_suitability"] < 80:
                    reason += " Workload proxy elevated."
        rows.append({"player_name": c["player_name"], "primary_role": c["primary_role"],
                     "minutes_before_decision": round(float(c["minutes_played"]), 0), "reason": reason})
    return pd.DataFrame(rows)


def compare_formations(ctx: DecisionContext, config: Config, unavailable: list | None = None) -> pd.DataFrame:
    rows = []
    for f in config.formation_templates:
        r = optimize_xi(ctx, f, config, unavailable)
        n = len(r.lineup)
        rows.append({"formation": f, "slots_filled": n, "total_score": round(r.total_score, 1),
                     "mean_slot_score": round(r.total_score / n, 1) if n else np.nan,
                     "mean_compatibility": round(r.lineup["compatibility"].mean(), 2) if n else np.nan,
                     "low_coverage_picks": int(r.lineup["coverage_label"].isin(
                         ["low data coverage", "no pre-decision minutes"]).sum()) if n else 0,
                     "warnings": len(r.warnings)})
    return pd.DataFrame(rows).sort_values("total_score", ascending=False).reset_index(drop=True)


def actual_xi(appearances: pd.DataFrame, match_id: Any, team_id: Any) -> pd.DataFrame:
    a = appearances[(appearances["match_id"] == match_id) & (appearances["team_id"] == team_id)
                    & appearances["is_starter"]]
    return a[["player_id", "player_name", "match_position", "match_role", "minutes_played"]].reset_index(drop=True)


def compare_with_actual(result: XIResult, appearances: pd.DataFrame, match_id: Any, team_id: Any
                        ) -> tuple[pd.DataFrame, float]:
    """Descriptive agreement between recommended and actual XI (not a quality measure)."""
    act = actual_xi(appearances, match_id, team_id)
    rec_ids = set(result.lineup["player_id"]) if not result.lineup.empty else set()
    act_ids = set(act["player_id"])
    names = dict(zip(act["player_id"], act["player_name"]))
    names.update(dict(zip(result.lineup.get("player_id", []), result.lineup.get("player_name", []))))
    rows = [{"player_name": names.get(p), "in_recommended": p in rec_ids, "in_actual": p in act_ids}
            for p in sorted(rec_ids | act_ids, key=lambda p: str(names.get(p)))]
    agree = len(rec_ids & act_ids) / 11 if act_ids else np.nan
    return pd.DataFrame(rows), agree


def what_if(ctx: DecisionContext, base: XIResult, slot: str, player_id: Any, config: Config,
            unavailable: list | None = None) -> tuple[XIResult, float]:
    """Pin a player to a slot, re-optimise the rest, report the score change."""
    new = optimize_xi(ctx, base.formation, config, unavailable, forced={slot: player_id})
    return new, new.total_score - base.total_score


def historical_agreement(bundle: Any, team_name: str, formation_from_match: bool = True,
                         max_matches: int | None = None) -> pd.DataFrame:
    """Recommendation vs actual XI for each team match (descriptive agreement only)."""
    cfg = bundle.config
    ts = bundle.team_stats[bundle.team_stats["team_name"] == team_name].sort_values("match_date")
    rows = []
    for _, m in ts.iloc[1:].iterrows():  # skip first match: no pre-decision history
        f = m["starting_formation"] if formation_from_match else None
        if f not in cfg.formation_templates:
            f = "3-4-2-1" if "3-4-2-1" in cfg.formation_templates else next(iter(cfg.formation_templates))
            mapped = True
        else:
            mapped = False
        ctx = decision_context(bundle, team_name, match_id=m["match_id"])
        r = optimize_xi(ctx, f, cfg)
        _, agree = compare_with_actual(r, bundle.tables["appearances"], m["match_id"], ctx.team_id)
        rows.append({"match_id": m["match_id"], "match_date": m["match_date"], "opponent": m["opponent"],
                     "actual_formation": m["starting_formation"], "template_used": f,
                     "template_mapped": mapped, "agreement_pct": round(agree * 100, 1)})
        if max_matches and len(rows) >= max_matches:
            break
    return pd.DataFrame(rows)


def role_label(role: str | None) -> str:
    return ROLE_LABEL.get(role, str(role))
