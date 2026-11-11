"""Data Quality & Sources: where the data come from, what was validated and what is missing."""
from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from src.dashboard import components as ui
from src.dashboard import filters, layout, state
from src.data import provenance
from src.data.schemas import TABLE_CONTRACTS, check_contracts
from src.data.validators import event_type_coverage
from src.features.player_features import metric_dictionary
from src.reporting import report_builder
from src.visualization import audit

base, _, tm = layout.start("Data Quality & Sources", "Where do the data come from, under which terms, and can the "
                           "tables be trusted for the analyses built on them?", eyebrow="Reference")
ws = base  # this page always describes the full dataset, not the filtered scope
p = state.params(ws)
b = ws.bundle
man = b.manifest if isinstance(b.manifest, pd.DataFrame) else pd.DataFrame()
m = ws.tables["matches"]
q = b.quality

st.caption("This page describes the whole loaded dataset; the sidebar filters do not apply here.")
ui.kpi_row([
    ("Raw files", f"{len(man)}", "Files read from the source for this dataset."),
    ("Raw size", f"{man['bytes'].sum() / 1e6:.1f} MB" if len(man) else "—", None),
    ("Matches analysed", f"{len(m)}", f"{b.matches_available} published for this competition-season"),
    ("Events", f"{len(ws.tables['events']):,}", None),
    ("Players in squads", f"{ws.tables['appearances']['player_id'].nunique()}", None),
    ("Domain rules passed", f"{int((q['status'] == 'PASS').sum())}/{len(q)}", None),
])

view = filters.view_select("View", ["Source and manifest", "Validation", "Missingness", "Duplicates and outliers",
                                    "Schema and dictionary", "Coverage and lineage"], key="w_dq_view")

if view == "Source and manifest":
    left, right = st.columns([0.55, 0.45])
    with left:
        st.markdown("#### Source")
        kind = "SYNTHETIC TEST FIXTURE — not real data" if ws.synthetic else "official source data"
        st.markdown(
            f"- **Dataset:** StatsBomb Open Data ({kind})\n"
            f"- **Repository:** {provenance.SOURCE_REPOSITORY_URL}\n"
            f"- **Terms:** [StatsBomb Public Data User Agreement]({provenance.SOURCE_TERMS_URL})\n"
            f"- **Field documentation:** {provenance.SOURCE_DOCS_URL}\n"
            f"- **Scope:** {m['competition_name'].iloc[0]} {m['season_name'].iloc[0]} (competition "
            f"{ws.cfg.competition_id}, season {ws.cfg.season_id}), {m['match_date'].min():%d %b %Y} – "
            f"{m['match_date'].max():%d %b %Y}\n"
            f"- **Attribution:** {provenance.ATTRIBUTION_REQUIREMENT}")
        st.markdown("#### Terms as read from the source licence")
        for t in provenance.TERMS_SUMMARY:
            st.markdown(f"- {t}")
        st.caption("Because the data may not be redistributed, this repository contains no raw or processed event "
                   "tables. They are downloaded from the official repository on first run and cached locally.")
    with right:
        st.markdown("#### Retrieval")
        if len(man):
            w = man["file_written_utc"].replace("", pd.NA).dropna()
            st.markdown(f"- Files written to the local cache between **{w.min()}** and **{w.max()}** (UTC)\n"
                        f"- Failed files: **{int((man['status'] != 'ok').sum())}**\n"
                        f"- Every file has a SHA-256 hash in the manifest\n"
                        f"- This is historical data: nothing is polled or refreshed")
            by = man.groupby("resource").agg(files=("relative_path", "size"),
                                             MB=("bytes", lambda s: round(s.sum() / 1e6, 2))).reset_index()
            st.dataframe(by, hide_index=True, width="stretch")
            manifest = provenance.build_manifest(b, {"status": "not checked from the dashboard"})
            st.download_button("Download the provenance manifest (JSON)",
                               json.dumps(manifest, indent=1, default=str), file_name="source_manifest.json",
                               mime="application/json", key="dq_manifest", on_click="ignore",
                               icon=":material/download:")
        st.markdown("#### What is source, derived, external or synthetic")
        st.dataframe(pd.DataFrame([
            ("Official source data", "matches, managers, squads, events (parsed fields)"),
            ("Derived by this project", "minutes, flags, per-90, percentiles, team stats, xPts, xT, scores"),
            ("External enrichment", "none used"),
            ("Synthetic fixtures", "used only by the automated tests, watermarked wherever shown"),
        ], columns=["class", "content"]), hide_index=True, width="stretch")
    st.markdown("#### Source register")
    ui.table(provenance.source_register(), "source_register", key="dq_sources")
elif view == "Validation":
    ui.chart("A-016", ws, p, key="dq_val")
    left, right = st.columns(2)
    with left:
        st.markdown("**Domain rules**")
        ui.table(q, "validation_rules", key="dq_rules")
    with right:
        st.markdown("**Table contracts**")
        ui.table(check_contracts(b), "table_contracts", key="dq_contracts")
    issues = ws.tables.get("parse_issues")
    st.markdown("**Parser issue log**")
    if isinstance(issues, pd.DataFrame) and len(issues):
        ui.table(issues, "parse_issues", key="dq_issues")
    else:
        st.caption("No parser issues were logged.")
elif view == "Missingness":
    layout.note("Most gaps are <b>structural</b>: a qualifier such as shot xG or pass recipient exists only for its "
                "event type. Missing values are kept as missing and are never replaced by zero.")
    tbl = st.selectbox("Table", ["events", "appearances", "squads", "matches", "team_stats", "season_pct", "subs"],
                       key="w_dq_table")
    df = b.table(tbl) if tbl in ("team_stats", "season_pct", "subs") else ws.tables[tbl]
    left, right = st.columns(2)
    with left:
        ui.show(audit.missingness_bar(df, tbl), key="dq_miss_bar")
    with right:
        ui.show(audit.nullity_matrix(df, tbl), key="dq_miss_mat")
    ui.chart("A-005", ws, p, key="dq_miss_type")
    ui.table(event_type_coverage(ws.tables["events"]), "field_completeness_by_event_type", key="dq_cov_tbl",
             height=320)
elif view == "Duplicates and outliers":
    left, right = st.columns(2)
    with left:
        ui.chart("A-006", ws, p, key="dq_dup")
    with right:
        ui.chart("A-010", ws, p, key="dq_out")
    ui.table(audit.duplicate_audit_table(b), "duplicate_audit", key="dq_dup_tbl")
    ui.chart("A-008", ws, p, key="dq_num")
    col = st.selectbox("Categorical field", [c for c in audit.CATEGORICAL_EVENT_FIELDS
                                             if c in ws.tables["events"].columns], key="w_dq_cat")
    ui.show(audit.categorical_frequency(ws.tables["events"], col), key="dq_cat")
elif view == "Schema and dictionary":
    ui.chart("A-013", ws, p, key="dq_schema")
    tbl = st.selectbox("Browse a table", list(TABLE_CONTRACTS), key="w_dq_schema_table")
    c = TABLE_CONTRACTS[tbl]
    st.markdown(f"**{tbl}** — {c.description}  \nGrain: {c.grain} · key: `{', '.join(c.key)}` · origin: {c.origin}")
    prof = audit.profile_table(b)
    df = b.table(tbl)
    from src.data.validators import dq_profile

    ui.table(dq_profile(df, tbl)[["column", "dtype", "family", "missing_pct", "distinct"]], f"schema_{tbl}",
             key="dq_schema_tbl", height=360)
    st.markdown("**Metric dictionary**")
    ui.table(metric_dictionary(), "metric_dictionary", key="dq_metric_dict", height=360)
    st.markdown("**Derived metrics and scores**")
    ui.table(pd.DataFrame(report_builder.DERIVED_METRICS, columns=["metric", "formula", "inputs", "caveat"]),
             "derived_metrics", key="dq_derived")
else:
    left, right = st.columns(2)
    with left:
        ui.chart("A-001", ws, p, key="dq_comp")
    with right:
        ui.chart("A-011", ws, p, key="dq_funnel")
    ui.chart("A-012", ws, p, key="dq_feat")
    ui.chart("A-014", ws, p, key="dq_time")
    left, right = st.columns(2)
    with left:
        ui.chart("A-002", ws, p, key="dq_rows")
    with right:
        ui.chart("A-015", ws, p, key="dq_prov")
layout.footer()
