"""Statistical and model-diagnostic charts."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from src.features.player_features import label
from src.visualization.theme import DIV_SCALE, MUTED, NAVY, SEQ_SCALE, TEAL, _empty, _missing, add_banner


def correlation_heatmap(df: pd.DataFrame, cols: list[str], title: str = "Correlation (Spearman)",
                        banner: str | None = None) -> go.Figure:
    cols = [c for c in cols if c in (df.columns if df is not None else [])]
    if df is None or len(df) < 5 or len(cols) < 2:
        return _empty("Not enough rows/columns for a correlation matrix.", title)
    c = df[cols].corr(method="spearman")
    lab = [label(x) for x in cols]
    fig = go.Figure(go.Heatmap(z=c.values, x=lab, y=lab, zmin=-1, zmax=1, colorscale=DIV_SCALE,
                               text=c.round(2).values, texttemplate="%{text}", textfont=dict(size=9),
                               colorbar=dict(title="ρ")))
    fig.update_layout(title=f"{title} — n={len(df)}; association only, shared minutes/role drive many pairs",
                      height=620, xaxis=dict(tickangle=-45), margin=dict(l=170, b=150))
    return add_banner(fig, banner)


def feature_distributions(df: pd.DataFrame, metrics: list[str], title: str = "Feature distributions",
                          banner: str | None = None) -> go.Figure:
    metrics = [m for m in metrics if df is not None and m in df.columns]
    if not metrics or df is None or df.empty:
        return _empty("No data for distributions.", title)
    fig = go.Figure()
    for i, m in enumerate(metrics):
        fig.add_trace(go.Histogram(x=df[m].dropna(), nbinsx=30, visible=(i == 0), name=label(m), marker_color=TEAL,
                                   marker_line=dict(color="white", width=0.5)))
    buttons = [dict(label=label(m), method="update", args=[{"visible": [j == i for j in range(len(metrics))]},
                                                           {"xaxis.title.text": label(m)}])
               for i, m in enumerate(metrics)]
    fig.update_layout(title=title, xaxis_title=label(metrics[0]), yaxis_title="players", height=380,
                      updatemenus=[dict(buttons=buttons, x=1, xanchor="right", y=1.15)], showlegend=False)
    return add_banner(fig, banner)


def missingness_heatmap(cov: pd.DataFrame, title: str = "Field completeness by event type (%)",
                        banner: str | None = None) -> go.Figure:
    if cov is None or cov.empty:
        return _empty("No coverage table.", title)
    fig = go.Figure(go.Heatmap(z=cov.values, x=list(cov.columns), y=list(cov.index), zmin=0, zmax=100,
                               colorscale=SEQ_SCALE, text=cov.values.round(0), texttemplate="%{text}",
                               colorbar=dict(title="% present")))
    fig.update_layout(title=title + " — blanks are structural (e.g. pressures have no outcome), not errors",
                      height=520, margin=dict(l=140))
    return add_banner(fig, banner)


def confusion_matrix_chart(cm: np.ndarray, title: str = "Confusion matrix (test period)",
                           banner: str | None = None) -> go.Figure:
    if cm is None:
        return _empty("No fitted model.", title)
    lab = ["did not start", "started"]
    fig = go.Figure(go.Heatmap(z=cm, x=[f"pred: {x}" for x in lab], y=[f"actual: {x}" for x in lab],
                               colorscale=SEQ_SCALE, text=cm, texttemplate="%{text}", showscale=False))
    fig.update_layout(title=title, height=340, yaxis=dict(autorange="reversed"))
    return add_banner(fig, banner)


def roc_chart(roc: pd.DataFrame, auc: float, banner: str | None = None) -> go.Figure:
    msg = _missing(roc, ["fpr", "tpr"])
    if msg:
        return _empty(msg, "ROC curve")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=roc["fpr"], y=roc["tpr"], mode="lines", name=f"Logistic regression (AUC {auc:.3f})",
                             line=dict(color=NAVY, width=3)))
    fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", name="Chance", line=dict(color=MUTED, dash="dot")))
    fig.update_layout(title="ROC — chronological hold-out", xaxis_title="False positive rate",
                      yaxis_title="True positive rate", height=380)
    return add_banner(fig, banner)


def calibration_chart(cal: pd.DataFrame, banner: str | None = None) -> go.Figure:
    msg = _missing(cal, ["mean_pred", "observed_rate", "n"])
    if msg:
        return _empty(msg, "Calibration")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=cal["mean_pred"], y=cal["observed_rate"], mode="lines+markers+text", text=cal["n"],
                             textposition="top center", name="model", marker=dict(size=10, color=TEAL)))
    fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", name="perfect calibration",
                             line=dict(color=MUTED, dash="dot")))
    fig.update_layout(title="Calibration (labels = rows per bin)", xaxis_title="mean predicted probability",
                      yaxis_title="observed start rate", height=360)
    return add_banner(fig, banner)


def threshold_sensitivity_chart(season: pd.DataFrame, thresholds: list[float] | None = None,
                                banner: str | None = None) -> go.Figure:
    thresholds = thresholds or [0, 90, 180, 270, 450, 900, 1350]
    msg = _missing(season, ["minutes_played"])
    if msg:
        return _empty(msg, "Minutes threshold")
    n = [int((season["minutes_played"] >= t).sum()) for t in thresholds]
    fig = go.Figure(go.Scatter(x=thresholds, y=n, mode="lines+markers+text", text=n, textposition="top center",
                               line=dict(color=NAVY, width=3)))
    fig.update_layout(title="Eligible players vs minimum-minutes threshold", xaxis_title="minimum minutes",
                      yaxis_title="players eligible", height=320)
    return add_banner(fig, banner)


def clustered_correlation(season_pct: pd.DataFrame, metrics: list[str], min_minutes: float) -> go.Figure:
    """Spearman correlation heatmap reordered by hierarchical clustering of metrics."""
    from scipy.cluster.hierarchy import leaves_list, linkage
    from scipy.spatial.distance import squareform
    d = season_pct[season_pct["minutes_played"] >= min_minutes]
    metrics = [m for m in metrics if m in d]
    if len(d) < 10 or len(metrics) < 3:
        return _empty("Not enough data.", "Clustered correlation")
    c = d[metrics].corr(method="spearman").fillna(0)
    dist = squareform((1 - c.abs()).clip(lower=0).values, checks=False)
    order = [metrics[i] for i in leaves_list(linkage(dist, "average"))]
    c = c.loc[order, order]
    lab = [label(m) for m in order]
    fig = go.Figure(go.Heatmap(z=c.values, x=lab, y=lab, zmin=-1, zmax=1, colorscale=DIV_SCALE, text=c.round(2).values,
                               texttemplate="%{text}", textfont=dict(size=9), colorbar=dict(title="ρ")))
    fig.update_layout(title=f"Metric families — Spearman correlations ordered by hierarchical clustering (n={len(d)})",
                      height=620, xaxis=dict(tickangle=-45), yaxis=dict(autorange="reversed"), margin=dict(l=170, b=150))
    return fig
