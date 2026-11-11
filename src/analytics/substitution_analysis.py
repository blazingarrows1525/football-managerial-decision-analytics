"""Substitution scenario context, candidate ranking and descriptive impact windows."""
from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Any
from typing import TYPE_CHECKING

from src.config import ROLE_LABEL, compatibility, role_for_position
from src.features.match_state import men_on_pitch, score_at, state_label
from src.features.player_features import COUNT_COLS, _pct_of, add_percentiles, all_metric_columns, player_season_table, recent_form
from src.features.substitution_features import _windows, bench_at, on_pitch_at, substitution_decisions

if TYPE_CHECKING:
    from src.config import Config

HUMAN_NOTE = ("Decision support only: the coaching staff makes the final decision, with information "
              "(fitness, instructions, opponent changes, player feedback) that this dataset does not contain.")


def scenario_context(bundle: Any, match_id: Any, team_name: str, elapsed: float) -> dict[str, Any]:
    """Everything known at ``elapsed`` minutes of playing time — no later information."""
    cfg: Config = bundle.config
    t = bundle.tables
    matches, flags = t["matches"], bundle.flags
    mm = matches.set_index("match_id").loc[match_id]
    team_id = mm["home_team_id"] if mm["home_team"] == team_name else mm["away_team_id"]
    if mm["home_team"] != team_name and mm["away_team"] != team_name:
        raise ValueError(f"{team_name} did not play match {match_id}")
    opp_id = mm["away_team_id"] if team_id == mm["home_team_id"] else mm["home_team_id"]
    asof = mm["match_date"]
    tg, og = score_at(t["goals"], match_id, team_id, opp_id, elapsed=elapsed)
    men = men_on_pitch(t["sending_offs"], match_id, team_id, opp_id, elapsed=elapsed)
    before = flags[(flags["match_id"] == match_id) & (flags["elapsed_min"] < elapsed)]
    subs_used = before[(before["type"] == "Substitution") & (before["team_id"] == team_id)]
    rules = cfg.sub_rules
    win_used = len(set(w for w in _windows(subs_used, rules) if w > 0)) if len(subs_used) else 0
    period_now = int(before["period"].max()) if len(before) else 1
    max_subs = rules["max_substitutions"] + (rules["extra_time_additional_substitutions"] if period_now >= 3 else 0)
    max_win = rules["max_windows"] + (rules["extra_time_additional_windows"] if period_now >= 3 else 0)

    def team_block(tid):
        b = before[before["team_id"] == tid]
        return {"shots": int(b["shots"].sum()), "xg": round(float(b["xg"].sum()), 2),
                "passes": int(b["passes"].sum()), "pass_completion_pct": round(
                    100 * b["passes_completed"].sum() / max(b["passes"].sum(), 1), 1),
                "final_third_touches": int(b["final_third_touches"].sum()), "pressures": int(b["pressures"].sum()),
                "defensive_actions": int(b["defensive_actions"].sum())}

    pitch = on_pitch_at(t["spells"], match_id, team_id, elapsed)
    bench = bench_at(t["appearances"], t["spells"], match_id, team_id, elapsed)
    # In-match player stats up to the decision moment
    pb = before[before["team_id"] == team_id].dropna(subset=["player_id"])
    inm = pb.groupby("player_id")[COUNT_COLS].sum()
    pitch = pitch.merge(inm, left_on="player_id", right_index=True, how="left").fillna({c: 0 for c in COUNT_COLS})
    pitch["minutes_so_far"] = elapsed - pitch["start"]
    cards = before[(before["team_id"] == team_id) & (before["card"] == "Yellow Card")]["player_id"]
    pitch["booked"] = pitch["player_id"].isin(set(cards))
    pitch["role"] = pitch["position"].map(role_for_position)
    # Pre-match history (earlier matches only)
    season = player_season_table(bundle.pms, t["appearances"], cfg, asof=asof, matches=matches)
    season_pct = add_percentiles(season, all_metric_columns(cfg), cfg)
    form = recent_form(bundle.pms, season_pct, cfg, asof=asof)
    wl = bundle.workload[(bundle.workload["match_id"] == match_id) & (bundle.workload["team_id"] == team_id)]
    return {"match_id": match_id, "team_id": team_id, "team_name": team_name, "opponent_id": opp_id,
            "opponent": mm["away_team"] if team_id == mm["home_team_id"] else mm["home_team"],
            "home_away": "home" if team_id == mm["home_team_id"] else "away", "match_date": asof,
            "elapsed": elapsed, "period": period_now, "team_score": tg, "opponent_score": og,
            "goal_diff": tg - og, "game_state": state_label(tg - og), "man_advantage": men,
            "subs_used": len(subs_used), "subs_remaining": max_subs - len(subs_used),
            "windows_used": win_used, "windows_remaining": max_win - win_used, "rule_source": rules["source"],
            "team_live": team_block(team_id), "opponent_live": team_block(opp_id),
            "on_pitch": pitch, "bench": bench, "season_pct": season_pct, "form": form, "workload": wl}


def infer_intent(goal_diff: int, elapsed: float, man_advantage: int = 0) -> tuple[str, str]:
    """Transparent context prompt (not a law): trailing -> attack, leading -> protect, drawing -> balance."""
    if goal_diff < 0:
        return "attack", "Trailing: consider attacking / progression-focused options."
    if goal_diff > 0:
        if man_advantage < 0:
            return "protect", "Leading with a numerical disadvantage: prioritise defensive stability."
        return "protect", "Leading: consider defensive stability, ball retention and role coverage."
    if elapsed >= 75:
        return "balance", "Drawing late: balance chance creation against defensive risk."
    return "balance", "Drawing: balance control, chance creation and defensive risk."


def _intent_score(season_pct: pd.DataFrame, team_id: Any, player_ids: list, intent: str, config: Config
                  ) -> pd.Series:
    weights = config.sub_intent_metrics[intent]
    sp = season_pct[(season_pct["team_id"] == team_id) & season_pct["player_id"].isin(player_ids)]
    elig = season_pct[season_pct["eligible"].astype(bool)]
    num = np.zeros(len(sp))
    wsum = np.zeros(len(sp))
    for m, w in weights.items():
        if m not in sp.columns:
            continue
        # Intent fit is benchmarked against ALL eligible players (not role groups) because the
        # question is "who adds this quality", e.g. more goal threat when trailing.
        v = _pct_of(sp[m].to_numpy(dtype=float), elig[m].to_numpy(dtype=float))
        ok = ~np.isnan(v)
        num[ok] += w * v[ok]
        wsum[ok] += w
    with np.errstate(invalid="ignore", divide="ignore"):
        vals = np.where(wsum > 0, num / np.where(wsum > 0, wsum, 1), np.nan)
    return pd.Series(vals, index=sp["player_id"].values)


def rank_outgoing(ctx: dict[str, Any], intent: str, config: Config, include_gk: bool = False) -> pd.DataFrame:
    """Rank on-pitch players as substitution-off candidates with reasons.

    Components: minutes already played (proxy for load in this match), yellow-card
    risk, in-match involvement vs the player's OWN pre-match per-90 baseline for
    role-relevant actions (role context, not raw counts), and intent mismatch.
    """
    p = ctx["on_pitch"].copy()
    if p.empty:
        return p
    if not include_gk:
        p = p[p["role"] != "GK"]
    sp = ctx["season_pct"]
    base = sp[sp["team_id"] == ctx["team_id"]].set_index("player_id")
    role_w = config.role_metric_weights
    rows = []
    for _, r in p.iterrows():
        pid, role = r["player_id"], r["role"]
        mins = max(r["minutes_so_far"], 1.0)
        ratios, keys = [], []
        for m in role_w.get(role, {}):
            if not m.endswith("_p90"):
                continue
            b = m[:-4]
            if pid in base.index and pd.notna(base.loc[pid, m]) and base.loc[pid, m] > 0 and b in r:
                live = r[b] / mins * 90
                ratios.append(min(live / base.loc[pid, m], 2.0))
                keys.append(b)
        involvement = float(np.mean(ratios)) if ratios else np.nan
        fatigue_proxy = min(r["minutes_so_far"] / 90, 1.0) * 100
        intent_mismatch = 0.0
        if intent == "attack" and role in ("CB", "DM", "FB"):
            intent_mismatch = 60.0
        elif intent == "protect" and role in ("CF", "W", "AM"):
            intent_mismatch = 60.0
        low_inv = (1 - min(involvement, 1.0)) * 100 if pd.notna(involvement) else 30.0
        card = 100.0 if r["booked"] else 0.0
        score = 0.35 * fatigue_proxy + 0.30 * low_inv + 0.15 * card + 0.20 * intent_mismatch
        reasons = [f"{r['minutes_so_far']:.0f} min played this match"]
        if pd.notna(involvement):
            reasons.append(f"role-action rate at {involvement * 100:.0f}% of own pre-match baseline "
                           f"({len(keys)} role metrics)")
        else:
            reasons.append("no pre-match baseline (insufficient earlier minutes) — involvement not assessed")
        if r["booked"]:
            reasons.append("booked (second-yellow risk)")
        if intent_mismatch:
            reasons.append(f"role {role} less aligned with '{intent}' intent")
        rows.append({"player_id": pid, "player_name": r["player_name"], "position": r["position"], "role": role,
                     "minutes_so_far": round(r["minutes_so_far"], 1), "booked": r["booked"],
                     "involvement_vs_baseline": round(involvement, 2) if pd.notna(involvement) else np.nan,
                     "outgoing_score": round(score, 1), "reasons": "; ".join(reasons),
                     "baseline_coverage": base.loc[pid, "coverage_label"] if pid in base.index else "no history"})
    return pd.DataFrame(rows).sort_values("outgoing_score", ascending=False).reset_index(drop=True)


def rank_incoming(ctx: dict[str, Any], outgoing_role: str | None, intent: str, config: Config) -> pd.DataFrame:
    """Rank eligible bench players for an outgoing player's role and the tactical intent."""
    bench = ctx["bench"]
    if bench.empty:
        return pd.DataFrame()
    sp = ctx["season_pct"]
    team_sp = sp[sp["team_id"] == ctx["team_id"]].set_index("player_id")
    form = ctx["form"]
    form = form[form["team_id"] == ctx["team_id"]].set_index("player_id")
    intent_s = _intent_score(sp, ctx["team_id"], list(bench["player_id"]), intent, config)
    wl = ctx["workload"].set_index("player_id") if not ctx["workload"].empty else pd.DataFrame()
    w = config.sub_candidate_weights
    rows = []
    for _, b in bench.iterrows():
        pid = b["player_id"]
        role = team_sp.loc[pid, "primary_role"] if pid in team_sp.index else b.get("match_role")
        if role == "GK" and outgoing_role != "GK":
            continue
        comp = compatibility(role, outgoing_role, config.role_compatibility) if outgoing_role else 0.5
        # Intent can justify a role change (e.g. forward for a defender when trailing) at reduced weight.
        if comp == 0 and intent == "attack" and role in ("CF", "W", "AM"):
            comp = 0.4
        if comp == 0 and intent == "protect" and role in ("CB", "DM", "FB", "WB"):
            comp = 0.4
        if comp == 0:
            continue
        mins = float(team_sp.loc[pid, "minutes_played"]) if pid in team_sp.index else 0.0
        rel = float(team_sp.loc[pid, "sample_reliability"]) if pid in team_sp.index else 0.0
        intent_fit = float(intent_s.loc[pid]) if pid in intent_s.index else np.nan
        form_v = form.loc[pid, "form_score"] if pid in form.index else np.nan
        parts = {"role_compatibility": comp * 100, "intent_fit": intent_fit, "recent_form": form_v,
                 "sample_reliability": rel}
        score = sum(w[k] * (0.0 if pd.isna(v) else v) for k, v in parts.items())
        m7 = wl.loc[pid, "minutes_prev_7d"] if (not wl.empty and pid in wl.index) else np.nan
        evidence = [f"role {role} vs outgoing {outgoing_role}: compatibility {comp:.2f}"]
        evidence.append(f"'{intent}' metric fit {intent_fit:.0f}th pct" if pd.notna(intent_fit)
                        else "no pre-match per-90 sample for intent metrics")
        evidence.append(f"{mins:.0f} pre-match minutes")
        if pd.notna(form_v):
            evidence.append(f"recent form {form_v:.0f}")
        risks = []
        if rel < 30:
            risks.append("small evidence base")
        if comp < 0.6:
            risks.append("positional change — tactical reshuffle needed")
        if pd.notna(m7) and m7 > 150:
            risks.append(f"{m7:.0f} min in previous 7 days (dataset matches only)")
        rows.append({"player_id": pid, "player_name": b["player_name"], "role": role, **parts,
                     "candidate_score": round(score, 1), "evidence": "; ".join(evidence),
                     "risks": "; ".join(risks) if risks else "none flagged",
                     "injury_status": "unknown (no injury data in source — not assumed fit)"})
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("candidate_score", ascending=False).reset_index(drop=True)


def recommend_substitution(bundle: Any, match_id: Any, team_name: str, elapsed: float,
                           intent: str | None = None, n_alternatives: int = 3) -> dict[str, Any]:
    """Full explainable substitution recommendation at a decision moment."""
    cfg: Config = bundle.config
    ctx = scenario_context(bundle, match_id, team_name, elapsed)
    auto_intent, why = infer_intent(ctx["goal_diff"], elapsed, ctx["man_advantage"])
    intent = intent or auto_intent
    out = rank_outgoing(ctx, intent, cfg)
    result: dict[str, Any] = {"context": ctx, "intent": intent, "intent_reason": why if intent == auto_intent else
                              "user-selected intent", "outgoing_ranking": out, "human_note": HUMAN_NOTE}
    if ctx["subs_remaining"] <= 0 or ctx["windows_remaining"] <= 0:
        result["status"] = "No substitution allowance remaining under the configured rules."
        return result
    if out.empty or ctx["bench"].empty:
        result["status"] = "No eligible outgoing or incoming players."
        return result
    best = None
    for _, o in out.head(3).iterrows():
        inc = rank_incoming(ctx, o["role"], intent, cfg)
        if inc.empty:
            continue
        pair_score = 0.4 * o["outgoing_score"] + 0.6 * inc.iloc[0]["candidate_score"]
        if best is None or pair_score > best[0]:
            best = (pair_score, o, inc)
    if best is None:
        result["status"] = "No compatible bench candidate for the top outgoing options."
        return result
    _, o, inc = best
    top = inc.iloc[0]
    hist = bundle.subs[(bundle.subs["team_name"] == team_name) & (bundle.subs["game_state"] == ctx["game_state"])]
    if len(hist) >= 5:
        q1, q3 = hist["minute"].quantile([0.25, 0.75])
        window = f"team's historical {ctx['game_state']} substitutions mostly fall between {q1:.0f}' and {q3:.0f}'"
    else:
        window = "insufficient team history for this game state"
    cov = "high" if top["sample_reliability"] >= 70 else ("moderate" if top["sample_reliability"] >= 30 else "low")
    result.update({
        "status": "ok",
        "recommended_off": o.to_dict(), "recommended_on": top.to_dict(),
        "alternatives": inc.iloc[1:1 + n_alternatives][["player_name", "role", "candidate_score", "evidence",
                                                        "risks"]],
        "decision_window": f"now to ~{min(elapsed + 10, 90):.0f}' of playing time; {window}",
        "tactical_objective": {"attack": "increase chance creation and goal threat",
                               "protect": "protect the lead: defensive stability and ball retention",
                               "balance": "maintain control while adding a fresh option"}[intent],
        "coverage": f"{cov} data coverage for the incoming player",
        "rule_status": f"{ctx['subs_remaining']} substitutions and {ctx['windows_remaining']} windows remaining "
                       f"({ctx['rule_source']})",
    })
    return result


def sub_historical_agreement(bundle: Any, team_name: str, top_k: int = 3, max_subs: int | None = None,
                         skip_injury: bool = True) -> pd.DataFrame:
    """Re-run the heuristic one second before each real substitution (pre-decision data only)
    and record whether the actual incoming player was in the top-k. Descriptive agreement only."""
    cfg = bundle.config
    subs = bundle.subs[bundle.subs["team_name"] == team_name]
    if skip_injury:
        subs = subs[subs["sub_reason"] != "Injury"]
    rows = []
    for _, s in subs.iterrows():
        t = s["elapsed_min"] - 1 / 60
        if t <= 0:
            continue
        ctx = scenario_context(bundle, s["match_id"], team_name, t)
        intent, _ = infer_intent(ctx["goal_diff"], t, ctx["man_advantage"])
        out = rank_outgoing(ctx, intent, cfg)
        inc = rank_incoming(ctx, s["off_role"], intent, cfg)
        rank_on = (inc.index[inc["player_id"] == s["player_on_id"]][0] + 1
                   if not inc.empty and (inc["player_id"] == s["player_on_id"]).any() else np.nan)
        rank_off = (out.index[out["player_id"] == s["player_off_id"]][0] + 1
                    if not out.empty and (out["player_id"] == s["player_off_id"]).any() else np.nan)
        rows.append({"match_id": s["match_id"], "minute": s["minute"], "game_state": s["game_state"],
                     "actual_off": s["player_off_name"], "actual_on": s["player_on_name"],
                     "bench_size": len(ctx["bench"]), "rank_actual_on": rank_on,
                     "on_in_top_k": bool(rank_on <= top_k) if pd.notna(rank_on) else False,
                     "rank_actual_off": rank_off,
                     "off_in_top_k": bool(rank_off <= top_k) if pd.notna(rank_off) else False})
        if max_subs and len(rows) >= max_subs:
            break
    return pd.DataFrame(rows)


def impact_windows(bundle: Any, window: float | None = None) -> pd.DataFrame:
    """Team event rates per 15 minutes in equal windows before/after each substitution DECISION.

    The unit is a team's substitution decision (simultaneous changes grouped), so
    changes made together do not "contaminate" each other. Windows are truncated
    at kick-off/full-time and normalised by actual length. ``contaminated`` = a goal,
    sending-off or another decision by the same team inside the window; opponent
    changes are reported separately as a remaining confounder. These are OBSERVED
    ASSOCIATIONS, not causal effects.
    """
    w = window or bundle.config.impact_window_minutes
    flags, subs, goals, so = bundle.flags, bundle.subs, bundle.tables["goals"], bundle.tables["sending_offs"]
    lengths = bundle.tables["period_bounds"].groupby("match_id")["duration"].sum() / 60
    decisions = substitution_decisions(subs, bundle.config.sub_rules.get("window_grouping_seconds", 90))
    metrics = ["shots", "xg", "final_third_touches", "progressive_passes", "pressures"]
    rows = []
    for _, s in decisions.iterrows():
        mid, tid, opp, t = s["match_id"], s["team_id"], s["opponent_id"], s["elapsed_min"]
        end = lengths.get(mid, np.nan)
        pre0, post1 = max(t - w, 0), min(t + w, end)
        if t - pre0 < 3 or post1 - t < 3:
            continue
        ev = flags[flags["match_id"] == mid]
        rec = {"match_id": mid, "team_name": s["team_name"], "minute": s["minute"], "game_state": s["game_state"],
               "n_changes": s["n_changes"], "players_on": s["players_on"], "players_off": s["players_off"],
               "pre_len": t - pre0, "post_len": post1 - t}
        for side, tt in (("team", tid), ("opp", opp)):
            e = ev[ev["team_id"] == tt]
            pre = e[(e["elapsed_min"] >= pre0) & (e["elapsed_min"] < t)]
            post = e[(e["elapsed_min"] >= t) & (e["elapsed_min"] < post1)]
            for m in metrics:
                rec[f"{side}_{m}_pre15"] = pre[m].sum() / (t - pre0) * 15
                rec[f"{side}_{m}_post15"] = post[m].sum() / (post1 - t) * 15
        same = decisions[(decisions["match_id"] == mid) & (decisions["team_id"] == tid)
                         & (decisions["decision_id"] != s["decision_id"]) & decisions["elapsed_min"].between(pre0, post1)]
        opp_d = decisions[(decisions["match_id"] == mid) & (decisions["team_id"] == opp)
                          & decisions["elapsed_min"].between(pre0, post1)]
        g = goals[(goals["match_id"] == mid) & goals["elapsed_min"].between(pre0, post1)]
        r = so[(so["match_id"] == mid) & so["elapsed_min"].between(pre0, post1)]
        rec.update({"goal_in_window": len(g) > 0, "red_card_in_window": len(r) > 0,
                    "other_own_decision_in_window": len(same) > 0, "opponent_changed_in_window": len(opp_d) > 0})
        rec["contaminated"] = bool(len(g) or len(r) or len(same))
        rec["contamination"] = ", ".join(x for x, n in (("own other sub decision", len(same)), ("goal", len(g)),
                                                        ("red card", len(r))) if n) or "none"
        rows.append(rec)
    df = pd.DataFrame(rows)
    for m in metrics:
        if f"team_{m}_pre15" in df:
            df[f"delta_team_{m}"] = df[f"team_{m}_post15"] - df[f"team_{m}_pre15"]
    return df


def impact_summary(impact: pd.DataFrame, clean_only: bool = False) -> pd.DataFrame:
    """Median post-minus-pre change per 15 minutes by game state (association only)."""
    if impact.empty:
        return pd.DataFrame()
    d = impact[~impact["contaminated"]] if clean_only else impact
    if d.empty:
        return pd.DataFrame()
    cols = [c for c in d.columns if c.startswith("delta_team_")]
    g = d.groupby("game_state")
    out = g[cols].median().round(3)
    out.insert(0, "n_decisions", g.size())
    out.insert(1, "opponent_also_changed_pct", (g["opponent_changed_in_window"].mean() * 100).round(0))
    return out.reset_index()


def role_name(role: str | None) -> str:
    return ROLE_LABEL.get(role, str(role))
