"""Data-quality checks, coverage and missingness profiles for the canonical tables."""
from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Any

from src.config import PITCH_LENGTH, PITCH_WIDTH
from src.data.statsbomb_client import log


def dataset_scale(tables: dict[str, Any], manifest: pd.DataFrame, processing_seconds: float | None = None
                  ) -> pd.DataFrame:
    """Honest data-scale summary (rows, files, bytes) for the coverage cards."""
    ev, app, matches = tables["events"], tables["appearances"], tables["matches"]
    ok = manifest[manifest["status"] == "ok"] if not manifest.empty else manifest
    raw_bytes = float(ok["bytes"].sum()) if not ok.empty else 0.0
    rows = [
        ("Competitions", matches["competition_id"].nunique()),
        ("Seasons", matches["season_id"].nunique()),
        ("Matches listed by source (selected)", len(matches)),
        ("Matches parsed", int(matches["parsed"].sum()) if "parsed" in matches else len(matches)),
        ("Events parsed", len(ev)),
        ("Matchday-squad (lineup) rows", len(app)),
        ("Teams", pd.unique(pd.concat([matches["home_team_id"], matches["away_team_id"]])).size),
        ("Players (unique IDs in squads)", app["player_id"].nunique()),
        ("Substitutions", len(tables["substitutions_raw"])),
        ("Goals (periods 1-4)", len(tables["goals"])),
        ("Raw JSON files", len(ok)),
        ("Raw data size (MB)", round(raw_bytes / 1e6, 2)),
        ("Date range", f"{matches['match_date'].min():%Y-%m-%d} to {matches['match_date'].max():%Y-%m-%d}"
         if len(matches) else "n/a"),
    ]
    if processing_seconds is not None:
        rows.append(("Parse + build time (s)", round(processing_seconds, 1)))
    return pd.DataFrame(rows, columns=["measure", "value"])


def missingness(df: pd.DataFrame, columns: list[str] | None = None) -> pd.DataFrame:
    cols = columns or list(df.columns)
    cols = [c for c in cols if c in df.columns]
    if df.empty:
        return pd.DataFrame(columns=["field", "missing_pct", "non_missing"])
    m = df[cols].isna().mean() * 100
    return (pd.DataFrame({"field": cols, "missing_pct": m.values.round(2),
                          "non_missing": df[cols].notna().sum().values})
            .sort_values("missing_pct", ascending=False).reset_index(drop=True))


def event_type_coverage(events: pd.DataFrame) -> pd.DataFrame:
    """Field completeness per event type (for the coverage heatmap)."""
    fields = ["player_id", "team_id", "x", "y", "end_x", "outcome", "shot_xg", "pass_recipient_id", "position_name"]
    if events.empty:
        return pd.DataFrame()
    top = events["type"].value_counts().head(15).index
    sub = events[events["type"].isin(top)]
    return (sub.groupby("type")[fields].apply(lambda g: g.notna().mean() * 100)).round(1)


def quality_checks(tables: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run domain-rule checks. Returns (check_results, quality_action_log)."""
    ev, app, matches = tables["events"], tables["appearances"], tables["matches"]
    goals, subs = tables["goals"], tables["substitutions_raw"]
    results: list[dict] = []
    log: list[dict] = []

    def add(check: str, n_bad: int, n_total: int, rule: str, action: str = "flagged") -> None:
        results.append({"check": check, "rule": rule, "violations": int(n_bad), "checked": int(n_total),
                        "status": "PASS" if n_bad == 0 else "FLAG"})
        if n_bad:
            log.append({"check": check, "records": int(n_bad), "action": action})

    # Duplicates
    add("Duplicate event IDs", ev["event_id"].duplicated().sum(), len(ev), "event_id unique")
    add("Duplicate squad rows", app.duplicated(["match_id", "team_id", "player_id"]).sum(), len(app),
        "one row per player per match")
    # Coordinates
    has_xy = ev["x"].notna()
    bad_xy = has_xy & ~(ev["x"].between(0, PITCH_LENGTH) & ev["y"].between(0, PITCH_WIDTH))
    add("Event coordinates outside 120x80", bad_xy.sum(), has_xy.sum(), "0<=x<=120, 0<=y<=80")
    has_end = ev["end_x"].notna()
    bad_end = has_end & ~(ev["end_x"].between(0, PITCH_LENGTH + 2) & ev["end_y"].between(-2, PITCH_WIDTH + 2))
    add("End coordinates outside pitch (+2 tolerance)", bad_end.sum(), has_end.sum(), "end location on/near pitch")
    # xG plausibility
    xg = ev["shot_xg"].dropna()
    add("xG outside [0,1]", (~xg.between(0, 1)).sum(), len(xg), "0<=statsbomb_xg<=1")
    # Negative values
    add("Negative minutes played", (app["minutes_played"] < 0).sum(), app["minutes_played"].notna().sum(),
        "minutes >= 0")
    # Event order
    ordered = ev.groupby("match_id")["index"].apply(lambda s: s.is_monotonic_increasing)
    add("Matches with unordered event index", (~ordered).sum(), len(ordered), "event index increasing")
    clock = ev["minute"] * 60 + ev["second"]
    back = ev.assign(c=clock).groupby(["match_id", "period"])["c"].apply(lambda s: (s.diff() < -5).sum())
    add("Clock steps backwards >5s within period", int(back.sum()), len(ev), "timestamps ordered (flag only)")
    # Starting XI sanity
    starters = app[app["is_starter"]].groupby(["match_id", "team_id"]).size()
    add("Team-matches without exactly 11 starters", (starters != 11).sum(), len(starters), "XI has 11 players")
    gk = (app[app["is_starter"] & (app["match_role"] == "GK")].groupby(["match_id", "team_id"]).size()
          .reindex(starters.index, fill_value=0))
    add("Team-matches without exactly one starting GK", (gk != 1).sum(), len(starters),
        "one goalkeeper slot (event-position based)")
    dup_xi = app[app["is_starter"]].duplicated(["match_id", "team_id", "player_id"]).sum()
    add("Player selected twice in same XI", dup_xi, int(app["is_starter"].sum()), "XI players distinct")
    # Substitutions
    sub_bad = subs["player_off_id"].isna() | subs["player_on_id"].isna() | subs["team_id"].isna() | subs["minute"].isna()
    add("Substitutions missing team/player/time", sub_bad.sum(), len(subs), "complete substitution records")
    # Overlapping spells (same player on pitch twice at once)
    sp = tables["spells"]
    overlap = 0
    if not sp.empty:
        for _, g in sp.groupby(["match_id", "player_id"]):
            if len(g) > 1:
                g = g.sort_values("start")
                overlap += int((g["start"].values[1:] < g["end"].values[:-1]).sum())
    add("Overlapping on-pitch spells", overlap, len(sp), "player cannot be on pitch twice simultaneously")
    # Score reconciliation
    if not goals.empty and not matches.empty:
        gcount = goals.groupby(["match_id", "scoring_team_id"]).size()
        bad = 0
        for _, m in matches[matches["parsed"]].iterrows():
            hg = gcount.get((m["match_id"], m["home_team_id"]), 0)
            ag = gcount.get((m["match_id"], m["away_team_id"]), 0)
            if (hg, ag) != (m["home_score"], m["away_score"]):
                bad += 1
                log.append({"check": "Score reconciliation", "records": 1, "action":
                            f"match {m['match_id']}: events {hg}-{ag} vs metadata {m['home_score']}-{m['away_score']}"})
        results.append({"check": "Event goals != published score", "rule": "goal events reconcile to final score",
                        "violations": bad, "checked": int(matches["parsed"].sum()),
                        "status": "PASS" if bad == 0 else "FLAG"})
    # Unmatched references: event players absent from squads
    squad_ids = set(zip(app["match_id"], app["player_id"]))
    ev_players = ev.dropna(subset=["player_id"])[["match_id", "player_id"]].drop_duplicates()
    unmatched = sum((m, p) not in squad_ids for m, p in ev_players.itertuples(index=False))
    add("Event players missing from matchday squad", unmatched, len(ev_players), "player references resolve")
    # Minutes flags
    unk = app["minutes_flag"].astype(str).str.startswith("unknown").sum()
    add("Appearances with unknown minutes", unk, len(app), "minutes derivable from events")

    pi = tables.get("parse_issues")
    if pi is not None and not pi.empty:
        for _, r in pi.iterrows():
            log.append({"check": "parser", "records": 1, "action": f"{r.get('issue')} -> {r.get('action')}"})
    return pd.DataFrame(results), pd.DataFrame(log, columns=["check", "records", "action"])


def coverage_summary(tables: dict[str, Any]) -> pd.DataFrame:
    ev, app, matches = tables["events"], tables["appearances"], tables["matches"]
    lineup_matches = app["match_id"].nunique() if not app.empty else 0
    on_ball = ev[ev["type"].isin(["Pass", "Carry", "Shot", "Dribble", "Ball Receipt*", "Pressure", "Duel"])]
    rows = [
        ("Matches with lineup data (%)", round(100 * lineup_matches / max(len(matches), 1), 1)),
        ("Squad rows with position (appeared players) (%)",
         round(100 * app.loc[app["appeared"], "match_position"].notna().mean(), 1) if app["appeared"].any() else 0),
        ("On-ball events with coordinates (%)", round(100 * on_ball["x"].notna().mean(), 1) if len(on_ball) else 0),
        ("Shots with xG (%)", round(100 * ev.loc[ev["type"] == "Shot", "shot_xg"].notna().mean(), 1)
         if (ev["type"] == "Shot").any() else 0),
        ("Passes with recipient (%)", round(100 * ev.loc[ev["type"] == "Pass", "pass_recipient_id"].notna().mean(), 1)
         if (ev["type"] == "Pass").any() else 0),
        ("Matches with manager metadata (%)",
         round(100 * tables["managers"]["match_id"].nunique() / max(len(matches), 1), 1)),
        ("Matches with referee (%)", round(100 * matches["referee"].notna().mean(), 1) if len(matches) else 0),
        ("Matches with stadium (%)", round(100 * matches["stadium"].notna().mean(), 1) if len(matches) else 0),
        ("Attendance / weather / injuries", "not provided by source — not analysed"),
    ]
    return pd.DataFrame(rows, columns=["coverage measure", "value"])


def assert_no_nan_ids(df: pd.DataFrame, cols: list[str]) -> dict[str, int]:
    return {c: int(df[c].isna().sum()) for c in cols if c in df.columns}


def numeric_summary(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    cols = [c for c in cols if c in df.columns]
    if not cols:
        return pd.DataFrame()
    return df[cols].describe().T.round(3)


def suspicious_values(app: pd.DataFrame, max_minutes: float = 135.0) -> pd.DataFrame:
    """Appearances with implausible minutes (e.g. > 135 incl. extra time)."""
    return app[(app["minutes_played"] > max_minutes) | (app["minutes_played"] < 0)]


def dtype_family(dtype) -> str:
    if pd.api.types.is_bool_dtype(dtype):
        return "boolean"
    if pd.api.types.is_numeric_dtype(dtype):
        return "numeric"
    if pd.api.types.is_datetime64_any_dtype(dtype):
        return "datetime"
    return "categorical / text"


def dq_profile(df: pd.DataFrame, name: str) -> pd.DataFrame:
    """Column-level profile: dtype, family, missing %, distinct values."""
    rows = []
    for c in df.columns:
        try:
            nun = df[c].nunique(dropna=True)
        except TypeError:  # nested lists (e.g. tactics lineups) are not hashable
            nun = np.nan
        rows.append({"table": name, "column": c, "dtype": str(df[c].dtype), "family": dtype_family(df[c].dtype),
                     "missing_pct": round(df[c].isna().mean() * 100, 2), "distinct": nun})
    return pd.DataFrame(rows)


def iqr_outliers(s: pd.Series) -> int:
    s = s.dropna()
    q1, q3 = s.quantile([0.25, 0.75])
    return int(((s < q1 - 1.5 * (q3 - q1)) | (s > q3 + 1.5 * (q3 - q1))).sum())
