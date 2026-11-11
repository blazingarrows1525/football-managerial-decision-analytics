"""Data-audit and coverage charts (catalogue family A)."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.data.schemas import ANALYTICAL_TABLES, TABLE_CONTRACTS, check_contracts
from src.data.validators import dq_profile, dtype_family, iqr_outliers
from src.visualization.theme import (AMBER, COLORWAY, GRID, NAVY, RED, SLATE, TEAL,
                                     _empty, sub, table_figure)

NUMERIC_EVENT_FIELDS = {"duration": "seconds", "pass_length": "pitch units (120 = pitch length)",
                        "shot_xg": "probability", "x": "pitch units", "y": "pitch units"}
CATEGORICAL_EVENT_FIELDS = ["type", "play_pattern", "outcome", "pass_height", "pass_type", "shot_body_part",
                            "shot_type", "position_name", "duel_type", "goalkeeper_type", "card"]
KEYS = {"matches": ["match_id"], "events": ["event_id"], "squads": ["match_id", "team_id", "player_id"],
        "appearances": ["match_id", "player_id"], "pms": ["match_id", "player_id"],
        "season_pct": ["player_id", "team_id"], "team_stats": ["match_id", "team_id"],
        "subs": ["match_id", "event_id"]}


def _tables(bundle: Any) -> dict[str, pd.DataFrame]:
    out = {k: v for k, v in bundle.tables.items() if isinstance(v, pd.DataFrame) and len(v.columns)}
    for k in ANALYTICAL_TABLES:
        v = getattr(bundle, k, None)
        if isinstance(v, pd.DataFrame):
            out[k] = v
    return out


def _nested(col: pd.Series) -> bool:
    """True for object columns holding lists / dicts / arrays (not hashable, so excluded from duplicate checks)."""
    if col.dtype != object:
        return False
    first = col.dropna()
    return bool(len(first)) and isinstance(first.iloc[0], (list, dict, np.ndarray))


def dataset_composition(bundle: Any) -> go.Figure:
    """Rows and columns of every canonical and derived table (log scale: sizes span four orders of magnitude)."""
    t = _tables(bundle)
    if not t:
        return _empty("No tables loaded.", "Dataset composition")
    d = pd.DataFrame([{"table": k, "rows": len(v), "columns": v.shape[1],
                       "origin": TABLE_CONTRACTS[k].origin if k in TABLE_CONTRACTS else "derived"}
                      for k, v in t.items()]).sort_values("rows")
    d = d[d["rows"] > 0]
    fig = go.Figure(go.Bar(y=d["table"], x=d["rows"], orientation="h",
                           marker_color=[NAVY if o == "source" else TEAL for o in d["origin"]],
                           text=[f"{r:,} rows · {c} cols" for r, c in zip(d["rows"], d["columns"])],
                           textposition="outside", cliponaxis=False,
                           hovertemplate="%{y}: %{x:,} rows<extra></extra>"))
    fig.update_layout(title=sub("Dataset composition by table",
                                "navy = parsed from source files · teal = derived by this project · log scale"),
                      xaxis=dict(type="log", title="rows (log scale)"), height=max(380, 26 * len(d) + 120),
                      margin=dict(l=150, r=140))
    return fig


def rows_by_entity(bundle: Any, entity: str = "match") -> go.Figure:
    """Event rows per match, team or player (top 30 for players)."""
    ev = bundle.tables.get("events")
    if ev is None or ev.empty:
        return _empty("No events loaded.", "Event rows by entity")
    if entity == "team":
        s = ev.groupby("team_name").size().sort_values()
        title, unit = "Event rows by team", "teams"
    elif entity == "player":
        s = ev.dropna(subset=["player_name"]).groupby("player_name").size().sort_values().tail(30)
        title, unit = "Event rows by player (30 most involved)", "players shown"
    else:
        m = bundle.tables["matches"].set_index("match_id")
        s = ev.groupby("match_id").size()
        s.index = [f"{m.loc[i, 'match_date']:%d %b %y} {m.loc[i, 'home_team'][:10]}–{m.loc[i, 'away_team'][:10]}"
                   if i in m.index else str(i) for i in s.index]
        title, unit = "Event rows by match", "matches"
    fig = go.Figure(go.Bar(y=s.index.astype(str), x=s.values, orientation="h", marker_color=NAVY,
                           hovertemplate="%{y}: %{x:,} events<extra></extra>"))
    fig.update_layout(title=sub(title, f"{len(s)} {unit} · {int(s.sum()):,} event rows · median {s.median():,.0f}"),
                      xaxis_title="event rows", height=max(380, 17 * len(s) + 130), margin=dict(l=220),
                      yaxis=dict(tickfont=dict(size=9)))
    return fig


def missingness_bar(df: pd.DataFrame | None, name: str = "events", top: int = 35) -> go.Figure:
    """Share of missing values per field. For event data most gaps are structural (type-specific qualifiers)."""
    if df is None or df.empty:
        return _empty("No rows.", f"Missing values — {name}")
    miss = df.isna().mean().mul(100).sort_values(ascending=False)
    miss = miss[miss > 0].head(top).iloc[::-1]
    if miss.empty:
        return _empty(f"No missing values in {name} ({len(df):,} rows, {df.shape[1]} columns).",
                      f"Missing values — {name}")
    fig = go.Figure(go.Bar(y=miss.index, x=miss.values, orientation="h",
                           marker_color=[RED if v > 95 else AMBER if v > 50 else TEAL for v in miss.values],
                           text=[f"{v:.1f}%" for v in miss.values], textposition="outside", cliponaxis=False,
                           hovertemplate="%{y}: %{x:.2f}% missing<extra></extra>"))
    fig.update_layout(title=sub(f"Missing values by field — {name}",
                                f"{len(df):,} rows · {int((df.isna().mean() > 0).sum())} of {df.shape[1]} fields have "
                                f"gaps · missing ≠ zero: qualifiers exist only for their event type"),
                      xaxis=dict(title="% of rows missing", range=[0, 112]),
                      height=max(380, 19 * len(miss) + 130), margin=dict(l=190))
    return fig


def nullity_matrix(df: pd.DataFrame | None, name: str = "events", sample: int = 400, seed: int = 0) -> go.Figure:
    """Row-by-field nullity matrix on a random sample of rows kept in original order (dark = present)."""
    if df is None or df.empty:
        return _empty("No rows.", f"Nullity matrix — {name}")
    rng = np.random.default_rng(seed)
    idx = np.sort(rng.choice(len(df), min(sample, len(df)), replace=False))
    d = df.iloc[idx]
    cols = [c for c in d.columns if d[c].isna().any()] or list(d.columns[:20])
    z = d[cols].notna().to_numpy().astype(int)
    fig = go.Figure(go.Heatmap(z=z, x=cols, y=np.arange(len(d)), colorscale=[[0, "#f1ede4"], [1, NAVY]],
                               showscale=False, hovertemplate="field %{x}<br>sampled row %{y}<extra></extra>"))
    fig.update_layout(title=sub(f"Nullity matrix — {name}",
                                f"random sample of {len(d):,} of {len(df):,} rows (seed {seed}), original order · "
                                f"navy = value present · {len(cols)} fields with at least one gap"),
                      height=560, xaxis=dict(tickangle=-60, tickfont=dict(size=9)),
                      yaxis=dict(title="sampled rows", showticklabels=False, autorange="reversed"))
    return fig


def duplicate_audit_table(bundle: Any) -> pd.DataFrame:
    """Full-row and primary-key duplicate counts per table."""
    rows = []
    for name, df in _tables(bundle).items():
        simple = df[[c for c in df.columns if not _nested(df[c])]]
        key = KEYS.get(name) or (list(TABLE_CONTRACTS[name].key) if name in TABLE_CONTRACTS else None)
        rows.append({"table": name, "rows": len(df), "full_row_duplicates": int(simple.duplicated().sum()),
                     "key": ", ".join(key) if key else "—",
                     "key_duplicates": int(df.duplicated(key).sum()) if key and all(k in df for k in key) else None})
    return pd.DataFrame(rows)


def duplicate_audit(bundle: Any) -> go.Figure:
    """Duplicate full rows and duplicate primary keys per table (a zero is a result, not a gap)."""
    d = duplicate_audit_table(bundle)
    if d.empty:
        return _empty("No tables loaded.", "Duplicate audit")
    fig = go.Figure()
    fig.add_bar(y=d["table"], x=d["full_row_duplicates"], orientation="h", name="full-row duplicates",
                marker_color=AMBER)
    fig.add_bar(y=d["table"], x=d["key_duplicates"].fillna(0), orientation="h", name="primary-key duplicates",
                marker_color=RED)
    total = int(d["full_row_duplicates"].sum() + d["key_duplicates"].fillna(0).sum())
    fig.update_layout(barmode="group", title=sub("Duplicate audit", f"{len(d)} tables checked · {total} duplicates "
                                                 f"found in total · keys listed in the audit table"),
                      xaxis=dict(title="duplicate rows", rangemode="tozero", range=[0, max(1, total) * 1.2]),
                      height=max(380, 24 * len(d) + 140), margin=dict(l=150), legend=dict(orientation="h", y=1.06))
    return fig


def duplicate_table(bundle: Any) -> go.Figure:
    return table_figure(duplicate_audit_table(bundle), "Duplicate-ID investigation table")


def numeric_distributions(events: pd.DataFrame | None) -> go.Figure:
    """Histogram of each numeric event field with its skewness (motivates medians and rank statistics)."""
    if events is None or events.empty:
        return _empty("No events loaded.", "Numeric distributions")
    fields = [f for f in NUMERIC_EVENT_FIELDS if f in events.columns and events[f].notna().sum() > 10]
    if not fields:
        return _empty("No numeric event fields available.", "Numeric distributions")
    fig = make_subplots(rows=1, cols=len(fields),
                        subplot_titles=[f"{f} (skew {events[f].dropna().skew():.1f})" for f in fields])
    for i, f in enumerate(fields, 1):
        v = events[f].dropna()
        hi = v.quantile(0.995)
        fig.add_trace(go.Histogram(x=v.clip(upper=hi), nbinsx=40, marker_color=COLORWAY[(i - 1) % len(COLORWAY)],
                                   showlegend=False, hovertemplate="%{x}: %{y:,} events<extra></extra>"), 1, i)
        fig.update_xaxes(title_text=NUMERIC_EVENT_FIELDS[f], row=1, col=i, title_font=dict(size=10))
    fig.update_layout(title=sub("Numeric event fields — distributions",
                                "values above the 99.5th percentile are clipped into the last bin for display only"),
                      height=380, bargap=0.02)
    return fig


def categorical_frequency(events: pd.DataFrame | None, column: str = "type", top: int = 25) -> go.Figure:
    """Category frequencies on a log axis; rare categories (< 0.5% of non-missing rows) are highlighted."""
    if events is None or column not in events.columns:
        return _empty(f"Field '{column}' is not available.", "Categorical frequency")
    s = events[column].dropna().astype(str).value_counts()
    if s.empty:
        return _empty(f"Field '{column}' has no values.", "Categorical frequency")
    share = s / s.sum()
    d = s.head(top).iloc[::-1]
    rare = int((share < 0.005).sum())
    fig = go.Figure(go.Bar(y=d.index, x=d.values, orientation="h",
                           marker_color=[AMBER if share[k] < 0.005 else NAVY for k in d.index],
                           text=[f"{share[k]:.1%}" for k in d.index], textposition="outside", cliponaxis=False,
                           hovertemplate="%{y}: %{x:,}<extra></extra>"))
    fig.update_layout(title=sub(f"Category frequency — {column}",
                                f"{len(s)} levels · {int(s.sum()):,} non-missing rows · {rare} rare levels (< 0.5%, "
                                f"amber) · log scale"),
                      xaxis=dict(type="log", title="rows (log scale)"), height=max(380, 20 * len(d) + 130),
                      margin=dict(l=190, r=70))
    return fig


def outlier_boxes(events: pd.DataFrame | None) -> go.Figure:
    """Box plots of numeric event fields with the count beyond 1.5 x IQR (retained: they are real events)."""
    if events is None or events.empty:
        return _empty("No events loaded.", "Outlier audit")
    fields = [f for f in ("duration", "pass_length", "shot_xg") if f in events.columns]
    if not fields:
        return _empty("No numeric event fields available.", "Outlier audit")
    fig = make_subplots(rows=1, cols=len(fields), subplot_titles=[
        f"{f}: {iqr_outliers(events[f].dropna()):,} beyond 1.5×IQR" for f in fields])
    rng = np.random.default_rng(0)
    for i, f in enumerate(fields, 1):
        v = events[f].dropna()
        v = v.iloc[np.sort(rng.choice(len(v), min(len(v), 6000), replace=False))]
        fig.add_trace(go.Box(y=v, name=f, marker_color=COLORWAY[i - 1], boxpoints="outliers", marker_size=3,
                             showlegend=False), 1, i)
    fig.update_layout(title=sub("Outlier audit of numeric event fields",
                                "up to 6,000 sampled values per field are drawn; counts in panel titles use all rows · "
                                "flagged values are genuine (long passes, penalties) and are kept"), height=420)
    return fig


def refinement_table(bundle: Any) -> pd.DataFrame:
    """Row counts at each refinement step, from raw events to the analysed feature tables."""
    ev = bundle.tables["events"]
    fl = bundle.flags
    app = bundle.tables["appearances"]
    return pd.DataFrame([
        ("Raw event rows parsed", len(ev)),
        ("Events with a location", int(ev["x"].notna().sum())),
        ("On-ball events with a player", int((fl["player_id"].notna() & fl["x"].notna()).sum())),
        ("Match-day squad rows", len(app)),
        ("Appearances with minutes > 0", int((app["minutes_played"] > 0).sum())),
        ("Player-season rows", len(bundle.season)),
        ("Players passing the minutes threshold", int(bundle.season["eligible"].sum())),
    ], columns=["step", "rows"])


def refinement_funnel(bundle: Any) -> go.Figure:
    """What survives each refinement step. No raw row is deleted; later steps are filters or aggregations."""
    d = refinement_table(bundle)
    fig = go.Figure(go.Bar(y=d["step"], x=d["rows"], orientation="h", marker_color=COLORWAY[:len(d)] + [SLATE] * 3,
                           text=[f"{v:,}" for v in d["rows"]], textposition="outside", cliponaxis=False))
    fig.update_layout(title=sub("Data refinement — rows at each step",
                                f"minutes threshold {bundle.config.min_minutes:.0f} · raw rows are never deleted; "
                                f"steps are filters and aggregations · log scale"),
                      xaxis=dict(type="log", title="rows (log scale)"), yaxis=dict(autorange="reversed"),
                      height=400, margin=dict(l=260, r=80))
    return fig


FEATURE_GROUPS: dict[str, tuple[str, list[str]]] = {
    "Event location (x, y)": ("events", ["x", "y"]),
    "Pass end location": ("events", ["end_x", "end_y"]),
    "Pass recipient": ("events", ["pass_recipient_id"]),
    "StatsBomb shot xG": ("events", ["shot_xg"]),
    "Shot body part / technique": ("events", ["shot_body_part", "shot_technique"]),
    "Pressure / counterpress flags": ("events", ["under_pressure", "counterpress"]),
    "Formation records": ("formations", ["formation"]),
    "Match-day squads incl. bench": ("squads", ["player_id", "jersey_number"]),
    "Manager identity": ("managers", ["manager_name"]),
    "Referee": ("matches", ["referee"]),
    "Stadium": ("matches", ["stadium"]),
    "Player nationality": ("squads", ["nationality"]),
    "Player age / date of birth": ("squads", ["birth_date", "age"]),
    "Player height / weight": ("squads", ["height", "weight"]),
    "Injury / availability status": ("squads", ["injury_status"]),
    "Physical load (GPS, sprints)": ("events", ["distance_covered", "sprints"]),
    "Tracking positions (all players)": ("tracking", ["frame"]),
    "360 freeze frames": ("frames_360", ["freeze_frame"]),
    "Post-shot xG (PSxG)": ("events", ["shot_psxg"]),
    "Attendance / weather": ("matches", ["attendance", "weather"]),
    "Market value / salary": ("squads", ["market_value", "salary"]),
}


def feature_availability_table(bundle: Any) -> pd.DataFrame:
    """Which analytical inputs exist in the loaded data: verified from the tables, not assumed."""
    rows = []
    for name, (table, cols) in FEATURE_GROUPS.items():
        df = bundle.table(table)
        have = [c for c in cols if df is not None and c in df.columns]
        cov = float(np.mean([df[c].notna().mean() for c in have]) * 100) if have and len(df) else 0.0
        scoped = cov
        if table == "events" and have and name in ("Pass end location", "Pass recipient"):
            p = df[df["type"] == "Pass"]
            scoped = float(np.mean([p[c].notna().mean() for c in have]) * 100) if len(p) else 0.0
        elif table == "events" and have and name.startswith(("StatsBomb shot xG", "Shot body part")):
            s = df[df["type"] == "Shot"]
            scoped = float(np.mean([s[c].notna().mean() for c in have]) * 100) if len(s) else 0.0
        status = "available" if have and scoped > 0 else "not in source data"
        if table == "frames_360" and status != "available":
            cat = bundle.catalogue
            sel = cat[(cat["competition_id"] == bundle.config.competition_id)
                      & (cat["season_id"] == bundle.config.season_id)] if isinstance(cat, pd.DataFrame) else None
            if sel is not None and len(sel) and sel["match_available_360"].notna().any():
                status = "published by source, not loaded"
        rows.append({"feature": name, "table": table, "fields_checked": ", ".join(cols),
                     "pct_of_all_rows": round(cov, 1), "pct_of_relevant_rows": round(scoped, 1), "status": status})
    return pd.DataFrame(rows)


def feature_availability(bundle: Any) -> go.Figure:
    """Verified availability of analytical inputs; absent modalities are listed rather than imputed."""
    d = feature_availability_table(bundle).iloc[::-1]
    fig = go.Figure(go.Bar(y=d["feature"], x=d["pct_of_relevant_rows"], orientation="h",
                           marker_color=[TEAL if s == "available" else "#d9d4c7" for s in d["status"]],
                           text=[f"{v:.0f}%" if s == "available" else s
                                 for v, s in zip(d["pct_of_relevant_rows"], d["status"])],
                           textposition="outside", cliponaxis=False,
                           customdata=d[["table", "fields_checked"]].to_numpy(),
                           hovertemplate="%{y}<br>table: %{customdata[0]} · fields: %{customdata[1]}<extra></extra>"))
    n_ok = int((d["status"] == "available").sum())
    fig.update_layout(title=sub("Verified feature availability",
                                f"{n_ok} of {len(d)} input groups present · % of relevant rows (e.g. xG is checked on "
                                f"shots only) · absent inputs are never imputed"),
                      xaxis=dict(title="% of relevant rows with a value", range=[0, 135]),
                      height=max(420, 24 * len(d) + 130), margin=dict(l=240))
    return fig


def schema_overview(bundle: Any) -> go.Figure:
    """Number of fields per table by data-type family."""
    rows = []
    for name, df in _tables(bundle).items():
        for fam, n in pd.Series([dtype_family(t) for t in df.dtypes]).value_counts().items():
            rows.append({"table": name, "family": fam, "fields": int(n)})
    d = pd.DataFrame(rows)
    if d.empty:
        return _empty("No tables loaded.", "Schema overview")
    piv = d.pivot_table(index="table", columns="family", values="fields", fill_value=0)
    piv = piv.loc[piv.sum(axis=1).sort_values().index]
    fig = go.Figure()
    for i, fam in enumerate(piv.columns):
        fig.add_bar(y=piv.index, x=piv[fam], orientation="h", name=fam, marker_color=COLORWAY[i % len(COLORWAY)])
    fig.update_layout(barmode="stack", title=sub("Schema overview — fields per table by data type",
                                                 f"{len(piv)} tables · {int(piv.values.sum())} fields in total"),
                      xaxis_title="fields", height=max(400, 24 * len(piv) + 130), margin=dict(l=150),
                      legend=dict(orientation="h", y=1.06))
    return fig


def time_coverage_table(bundle: Any) -> pd.DataFrame:
    """Per match: date, events, and the longest gap between consecutive events inside a period."""
    ev = bundle.tables["events"].sort_values(["match_id", "period", "index"])
    gap = ev.groupby(["match_id", "period"])["elapsed_min"].diff()
    g = pd.DataFrame({"match_id": ev["match_id"], "gap_min": gap}).groupby("match_id")["gap_min"].max()
    m = bundle.tables["matches"][["match_id", "match_date", "home_team", "away_team"]]
    out = m.merge(ev.groupby("match_id").size().rename("events"), on="match_id", how="left")
    out = out.merge(g.rename("max_gap_min"), on="match_id", how="left").sort_values("match_date")
    out["days_since_previous"] = out["match_date"].diff().dt.days
    return out.reset_index(drop=True)


def time_coverage(bundle: Any) -> go.Figure:
    """Calendar coverage of the analysed matches and the largest within-period event gap per match."""
    d = time_coverage_table(bundle)
    if d.empty:
        return _empty("No matches loaded.", "Time coverage")
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1,
                        subplot_titles=["Events per match over the calendar",
                                        "Longest gap between consecutive events within a period (minutes)"])
    lab = d["home_team"].str[:12] + " – " + d["away_team"].str[:12]
    fig.add_trace(go.Scatter(x=d["match_date"], y=d["events"], mode="markers+lines", marker=dict(color=NAVY, size=8),
                             line=dict(color=GRID), text=lab, showlegend=False,
                             hovertemplate="%{text}<br>%{x|%d %b %Y}: %{y:,} events<extra></extra>"), 1, 1)
    fig.add_trace(go.Bar(x=d["match_date"], y=d["max_gap_min"], marker_color=TEAL, text=lab, showlegend=False,
                         hovertemplate="%{text}<br>longest gap %{y:.1f} min<extra></extra>"), 2, 1)
    gap_days = d["days_since_previous"].max()
    fig.update_layout(title=sub("Time coverage and event-timeline continuity",
                                f"{len(d)} matches, {d['match_date'].min():%d %b %Y} – {d['match_date'].max():%d %b %Y}"
                                f" · longest break between analysed matches {gap_days:.0f} days · long in-match gaps "
                                f"are stoppages (injuries, VAR), not missing data"), height=560)
    return fig


def provenance_graph(bundle: Any) -> go.Figure:
    """Lineage from source files to canonical tables, derived tables and outputs (Sankey; widths are not data)."""
    man = bundle.manifest if isinstance(bundle.manifest, pd.DataFrame) else pd.DataFrame()
    n = man.groupby("resource").size().to_dict() if len(man) else {}
    nodes = [f"competitions.json ({n.get('competitions', 0)})", f"matches/*.json ({n.get('matches', 0)})",
             f"lineups/*.json ({n.get('lineups', 0)})", f"events/*.json ({n.get('events', 0)})",
             "matches", "managers", "squads", "events", "appearances · spells", "goals · formations",
             "flags (event features)", "player match / season", "team match stats", "substitutions",
             "notebooks", "Streamlit dashboard", "reports"]
    links = [(0, 4), (1, 4), (1, 5), (2, 6), (3, 7), (7, 8), (6, 8), (7, 9), (7, 10), (10, 11), (8, 11), (10, 12),
             (9, 12), (4, 12), (5, 12), (8, 13), (9, 13), (11, 14), (12, 14), (13, 14), (11, 15), (12, 15),
             (13, 15), (11, 16), (12, 16)]
    color = [SLATE] * 4 + [NAVY] * 4 + [TEAL] * 6 + [AMBER] * 3
    fig = go.Figure(go.Sankey(node=dict(label=nodes, color=color, pad=18, thickness=16,
                                        line=dict(color="white", width=1)),
                              link=dict(source=[a for a, _ in links], target=[b for _, b in links],
                                        value=[1] * len(links), color="rgba(141,153,174,0.25)")))
    fig.update_layout(title=sub("Data provenance — from source files to outputs",
                                "grey = raw files (count read) · navy = parsed source tables · teal = derived tables · "
                                "amber = deliverables · link width carries no meaning"), height=520)
    return fig


def validation_panel(quality: pd.DataFrame | None, bundle: Any | None = None) -> go.Figure:
    """Pass / flag status of every domain rule with the number of records checked and violating."""
    if quality is None or quality.empty:
        return _empty("No validation results.", "Validation rules")
    q = quality.copy()
    if bundle is not None:
        c = check_contracts(bundle)
        q = pd.concat([q, pd.DataFrame({"check": "Table contract: " + c["table"], "rule": c["grain"],
                                        "violations": c["duplicate_keys"].fillna(0).astype(int)
                                        + c["missing_columns"].str.len().gt(0).astype(int),
                                        "checked": c["rows"], "status": c["status"]})], ignore_index=True)
    q = q.iloc[::-1]
    colors = [TEAL if s == "PASS" else AMBER if s in ("FLAG", "WARN") else RED for s in q["status"]]
    fig = go.Figure(go.Bar(y=q["check"], x=[1] * len(q), orientation="h", marker_color=colors,
                           text=[f"{s} · {int(v):,} violations / {int(c):,} checked"
                                 for s, v, c in zip(q["status"], q["violations"], q["checked"])],
                           textposition="inside", insidetextanchor="start", textfont=dict(color="white", size=11),
                           customdata=q["rule"], hovertemplate="%{y}<br>%{customdata}<extra></extra>"))
    n_pass = int((q["status"] == "PASS").sum())
    fig.update_layout(title=sub("Validation rules — pass / flag panel", f"{n_pass} of {len(q)} rules pass"),
                      xaxis=dict(visible=False), height=max(420, 24 * len(q) + 110), margin=dict(l=330))
    return fig


def profile_table(bundle: Any) -> pd.DataFrame:
    """Field-level profile (type, missing %, distinct values) across the main tables."""
    frames = [dq_profile(df, name) for name, df in _tables(bundle).items()
              if name in ("matches", "events", "squads", "appearances", "team_stats", "season_pct", "subs")]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
