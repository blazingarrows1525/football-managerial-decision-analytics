"""Model-diagnostic, dimensionality-reduction and clustering charts (catalogue family K).

The only supervised target that passes the sample gate is start selection (who starts for the focus team).
Every chart here takes the result dictionaries of ``src.analytics.models`` / ``clustering`` / ``explainability``
and shows an empty state when the gate was not met.
"""
from __future__ import annotations


import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.visualization.theme import (AMBER, COLORWAY, DIV_SCALE, FAMILY_COLORS, INK, MUTED, NAVY, PURPLE, RED,
                                     SLATE, TEAL, _empty, _missing, heat, sub)

GATE_MSG = "No model was fitted: the sample gate was not met, so the result would not be statistically supportable."
MODEL_COLORS = {"Logistic regression": NAVY, "Random forest": TEAL, "Gradient boosting": AMBER,
                "Baseline: started previous match": SLATE}


def _fitted(res: dict | None) -> bool:
    return bool(res) and bool(res.get("fitted"))


def _split_note(res: dict) -> str:
    s = res["split"]
    return (f"hold-out = last {s['test_matches']} matches (from {s['test_from']:%d %b %Y}), {s['test_rows']} rows, "
            f"{s['test_positive_rate']:.0%} starters")


def model_comparison_bars(res: dict | None, metric: str = "f1") -> go.Figure:
    """Cross-validated score of each model and the baseline rule (mean and SD across time-ordered folds)."""
    if not _fitted(res):
        return _empty(GATE_MSG, "Model comparison")
    cs = res["cv_summary"]
    d = pd.DataFrame({"mean": cs[(metric, "mean")], "sd": cs[(metric, "std")]}).dropna().sort_values("mean")
    fig = go.Figure(go.Bar(y=d.index, x=d["mean"], orientation="h",
                           marker_color=[MODEL_COLORS.get(m, PURPLE) for m in d.index],
                           error_x=dict(type="data", array=d["sd"], color=INK, thickness=1.5),
                           text=[f"{m:.3f} ± {s:.3f}" for m, s in zip(d["mean"], d["sd"])],
                           textposition="inside", insidetextanchor="start", textfont=dict(color="white")))
    n_folds = res["cv"]["fold"].nunique()
    fig.update_layout(title=sub(f"Start-selection models vs the baseline rule — {metric.upper().replace('_', '-')}",
                                f"expanding-window cross-validation, {n_folds} folds split by match (train always "
                                f"earlier than test) · bar = mean, whisker = SD across folds · {res['gate']['rows']} "
                                f"rows from {res['gate']['matches']} matches"),
                      xaxis=dict(title=metric.replace("_", " "), range=[0, 1]), height=360, margin=dict(l=250))
    return fig


def roc_multi(res: dict | None) -> go.Figure:
    """ROC curves of all models on the chronological hold-out, with the baseline rule as a point."""
    if not _fitted(res):
        return _empty(GATE_MSG, "ROC curves")
    fig = go.Figure()
    hold = res["holdout"].set_index("model")
    for name, c in res["curves"].items():
        fig.add_trace(go.Scatter(x=c["fpr"], y=c["tpr"], mode="lines", name=f"{name} (AUC "
                                 f"{hold.loc[name, 'roc_auc']:.3f})", line=dict(color=MODEL_COLORS.get(name), width=2.5)))
    bp = res["baseline_point"]
    fig.add_trace(go.Scatter(x=[bp["fpr"]], y=[bp["tpr"]], mode="markers", name="baseline rule",
                             marker=dict(symbol="star", size=15, color=RED)))
    fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", line=dict(color=MUTED, dash="dot"), name="chance",
                             hoverinfo="skip"))
    fig.update_layout(title=sub("ROC curves — chronological hold-out", _split_note(res)),
                      xaxis=dict(title="false positive rate", range=[0, 1]),
                      yaxis=dict(title="true positive rate", range=[0, 1.02]), height=460,
                      legend=dict(orientation="h", y=-0.2))
    return fig


def pr_multi(res: dict | None) -> go.Figure:
    """Precision-recall curves on the hold-out with the positive-class rate as the reference line."""
    if not _fitted(res):
        return _empty(GATE_MSG, "Precision–recall curves")
    fig = go.Figure()
    hold = res["holdout"].set_index("model")
    for name, c in res["curves"].items():
        fig.add_trace(go.Scatter(x=c["recall"], y=c["precision"], mode="lines", name=f"{name} (AP "
                                 f"{hold.loc[name, 'pr_auc']:.3f})", line=dict(color=MODEL_COLORS.get(name), width=2.5)))
    bp = res["baseline_point"]
    fig.add_trace(go.Scatter(x=[bp["recall"]], y=[bp["precision"]], mode="markers", name="baseline rule",
                             marker=dict(symbol="star", size=15, color=RED)))
    fig.add_hline(y=res["split"]["test_positive_rate"], line=dict(color=MUTED, dash="dot"),
                  annotation_text="share of starters")
    fig.update_layout(title=sub("Precision–recall curves — chronological hold-out", _split_note(res)),
                      xaxis=dict(title="recall", range=[0, 1]), yaxis=dict(title="precision", range=[0, 1.02]),
                      height=460, legend=dict(orientation="h", y=-0.2))
    return fig


def confusion_chart(res: dict | None) -> go.Figure:
    """Confusion matrix of the best model under the eleven-starters-per-match rule."""
    if not _fitted(res):
        return _empty(GATE_MSG, "Confusion matrix")
    cm = np.asarray(res["confusion_matrix"])
    fig = heat(cm, ["predicted: bench", "predicted: start"], ["actual: bench", "actual: start"], "", fmt=".0f",
               colorbar="rows", hover="%{y} · %{x}: %{z:.0f}<extra></extra>")
    acc = float(np.trace(cm) / cm.sum())
    fig.update_layout(title=sub(f"Confusion matrix — {res['best']}",
                                f"{_split_note(res)} · decision rule: the 11 highest probabilities per match start · "
                                f"accuracy {acc:.1%}"), height=400)
    return fig


def calibration_multi(res: dict | None) -> go.Figure:
    """Reliability diagram of the best model on the hold-out (bins with their sample sizes)."""
    if not _fitted(res):
        return _empty(GATE_MSG, "Calibration")
    cal = res["calibration"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", line=dict(color=MUTED, dash="dot"),
                             name="perfect calibration", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=cal["mean_pred"], y=cal["observed_rate"], mode="lines+markers+text",
                             text=[f"n={n}" for n in cal["n"]], textposition="top left",
                             marker=dict(size=8 + cal["n"] / cal["n"].max() * 14, color=NAVY),
                             line=dict(color=NAVY, width=2), name=res["best"]))
    brier = float(res["holdout"].set_index("model").loc[res["best"], "brier"])
    fig.update_layout(title=sub(f"Reliability diagram — {res['best']}",
                                f"{_split_note(res)} · five equal-width probability bins · Brier score {brier:.3f} · "
                                f"points above the line = the model under-states the start probability"),
                      xaxis=dict(title="mean predicted probability", range=[0, 1]),
                      yaxis=dict(title="observed share of starters", range=[0, 1.05]), height=440,
                      legend=dict(orientation="h", y=-0.2))
    return fig


def brier_bars(res: dict | None) -> go.Figure:
    """Brier score of each model on the hold-out against the baseline rule and the no-skill reference."""
    if not _fitted(res):
        return _empty(GATE_MSG, "Brier score comparison")
    h = res["holdout"].dropna(subset=["brier"]).sort_values("brier", ascending=False)
    p = res["split"]["test_positive_rate"]
    fig = go.Figure(go.Bar(y=h["model"], x=h["brier"], orientation="h",
                           marker_color=[MODEL_COLORS.get(m, PURPLE) for m in h["model"]],
                           text=[f"{v:.3f}" for v in h["brier"]], textposition="outside"))
    fig.add_vline(x=p * (1 - p), line=dict(color=MUTED, dash="dot"), annotation_text="always predict the base rate")
    fig.update_layout(title=sub("Brier score — chronological hold-out (lower is better)",
                                f"{_split_note(res)} · mean squared error of the predicted probability · the baseline "
                                f"rule predicts 0 or 1, so it is penalised fully when wrong"),
                      xaxis=dict(title="Brier score", rangemode="tozero"), height=340, margin=dict(l=250))
    return fig


def threshold_chart(res: dict | None) -> go.Figure:
    """Precision, recall and F1 of the best model as the probability threshold moves."""
    if not _fitted(res):
        return _empty(GATE_MSG, "Threshold trade-off")
    t = res["thresholds"]
    fig = go.Figure()
    for col, c in (("precision", NAVY), ("recall", TEAL), ("f1", AMBER)):
        fig.add_trace(go.Scatter(x=t["threshold"], y=t[col], mode="lines+markers", name=col,
                                 line=dict(color=c, width=2.5)))
    best = t.loc[t["f1"].idxmax()]
    fig.add_vline(x=best["threshold"], line=dict(color=MUTED, dash="dot"),
                  annotation_text=f"max F1 at {best['threshold']:.2f}")
    fig.update_layout(title=sub(f"Threshold trade-off — {res['best']}",
                                f"{_split_note(res)} · a fixed threshold predicts "
                                f"{best['predicted_starters_per_match']:.1f} starters per match at the F1-optimal cut; "
                                f"the reported metrics use the top-11 rule instead, which always predicts eleven"),
                      xaxis_title="probability threshold", yaxis=dict(title="score", range=[0, 1.02]), height=420,
                      legend=dict(orientation="h", y=-0.2))
    return fig


def permutation_chart(table: pd.DataFrame | None, res: dict | None) -> go.Figure:
    """Permutation importance on the hold-out."""
    if not _fitted(res):
        return _empty(GATE_MSG, "Permutation importance")
    msg = _missing(table, ["feature", "importance_mean", "importance_std"])
    if msg:
        return _empty(msg, "Permutation importance")
    fig = go.Figure(go.Bar(y=table["feature"], x=table["importance_mean"], orientation="h", marker_color=TEAL,
                           error_x=dict(type="data", array=table["importance_std"], color=INK, thickness=1.5)))
    fig.add_vline(x=0, line=dict(color=INK, width=1))
    fig.update_layout(title=sub(f"Permutation importance — {table['model'].iloc[0]}",
                                f"{_split_note(res)} · drop in ROC-AUC when a feature is shuffled (30 repeats, whisker "
                                f"= SD) · correlated features share credit · describes the model, not causal levers"),
                      xaxis_title="mean drop in ROC-AUC", height=400, margin=dict(l=220))
    return fig


def pdp_ice_chart(pdp: dict | None, res: dict | None) -> go.Figure:
    """Partial dependence (average) over individual conditional expectation curves for one feature."""
    if not _fitted(res) or not pdp:
        return _empty(GATE_MSG, "Partial dependence / ICE")
    fig = go.Figure()
    for row in pdp["ice"]:
        fig.add_trace(go.Scatter(x=pdp["grid"], y=row, mode="lines", line=dict(color="rgba(141,153,174,0.25)", width=1),
                                 showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=pdp["grid"], y=pdp["average"], mode="lines", name="partial dependence (average)",
                             line=dict(color=NAVY, width=3.5)))
    fig.update_layout(title=sub(f"Partial dependence and ICE — {pdp['feature']} ({pdp['model']})",
                                f"{len(pdp['ice'])} sampled hold-out rows (grey) of {pdp['n_rows']} · average effect on "
                                f"the predicted start probability with other features held at their observed values · "
                                f"unreliable where features are strongly correlated"),
                      xaxis_title=pdp["feature"], yaxis=dict(title="predicted start probability", range=[0, 1.02]),
                      height=440, legend=dict(orientation="h", y=-0.2))
    return fig


def shap_beeswarm(shap_res: dict | None) -> go.Figure:
    """SHAP summary: one point per hold-out row and feature, coloured by the feature's value."""
    if not shap_res or shap_res.get("status") != "ok":
        return _empty((shap_res or {}).get("status", "SHAP values are not available."), "SHAP summary")
    vals, feats, data = shap_res["values"], shap_res["features"], shap_res["data"]
    order = list(shap_res["mean_abs"].index[::-1])
    rng = np.random.default_rng(0)
    fig = go.Figure()
    for i, f in enumerate(order):
        j = feats.index(f)
        v = data[f].to_numpy(float)
        span = np.ptp(v) or 1.0
        fig.add_trace(go.Scatter(x=vals[:, j], y=i + rng.uniform(-0.28, 0.28, len(v)), mode="markers",
                                 marker=dict(size=5, color=(v - v.min()) / span, colorscale=[[0, TEAL], [1, RED]],
                                             opacity=0.75, showscale=i == 0,
                                             colorbar=dict(title="feature value", tickvals=[0, 1],
                                                           ticktext=["low", "high"], thickness=10, len=0.5)),
                                 showlegend=False, hovertemplate=f"{f}<br>SHAP %{{x:.2f}}<extra></extra>"))
    fig.add_vline(x=0, line=dict(color=INK, width=1))
    fig.update_layout(title=sub(f"SHAP summary — {shap_res['model']}",
                                f"{len(vals)} hold-out rows · contribution to the log-odds of starting · features "
                                f"ordered by mean |SHAP| · explains this model's predictions, not football causes"),
                      xaxis_title="SHAP value (log-odds)", yaxis=dict(tickvals=list(range(len(order))), ticktext=order),
                      height=max(400, 42 * len(order) + 140), margin=dict(l=220))
    return fig


def shap_dependence(shap_res: dict | None, feature: str | None = None) -> go.Figure:
    """SHAP value of one feature against the feature's value."""
    if not shap_res or shap_res.get("status") != "ok":
        return _empty((shap_res or {}).get("status", "SHAP values are not available."), "SHAP dependence")
    feature = feature or shap_res["mean_abs"].index[0]
    j = shap_res["features"].index(feature)
    fig = go.Figure(go.Scatter(x=shap_res["data"][feature], y=shap_res["values"][:, j], mode="markers",
                               marker=dict(size=7, color=NAVY, opacity=0.6)))
    fig.add_hline(y=0, line=dict(color=INK, width=1))
    fig.update_layout(title=sub(f"SHAP dependence — {feature}",
                                f"{len(shap_res['values'])} hold-out rows · {shap_res['model']} · vertical spread at a "
                                f"given x reflects interactions with other features"),
                      xaxis_title=feature, yaxis_title="SHAP value (log-odds)", height=420)
    return fig


def residual_hist(res: dict | None) -> go.Figure:
    """Distribution of probability residuals (actual minus predicted) on the hold-out, by outcome."""
    if not _fitted(res):
        return _empty(GATE_MSG, "Residual distribution")
    t = res["test_best"]
    fig = go.Figure()
    for y, name, c in ((1, "actual starters", NAVY), (0, "actual bench", AMBER)):
        g = t[t["y"] == y]
        fig.add_trace(go.Histogram(x=g["residual"], name=f"{name} (n={len(g)})", marker_color=c, opacity=0.75,
                                   xbins=dict(start=-1, end=1, size=0.1)))
    fig.update_layout(barmode="overlay", title=sub(f"Probability residuals — {res['best']}",
                                                   f"{_split_note(res)} · residual = actual (0/1) − predicted "
                                                   f"probability · mass near ±1 = confident errors"),
                      xaxis=dict(title="residual", range=[-1, 1]), yaxis_title="rows", height=400)
    return fig


def residual_vs_fitted(res: dict | None) -> go.Figure:
    """Mean residual by decile of predicted probability (a binned residual plot for a classifier)."""
    if not _fitted(res):
        return _empty(GATE_MSG, "Residuals vs fitted")
    t = res["test_best"]
    bins = pd.qcut(t["prob"], 8, duplicates="drop")
    g = t.groupby(bins, observed=True).agg(fitted=("prob", "mean"), resid=("residual", "mean"),
                                           se=("residual", lambda s: s.std() / np.sqrt(len(s))), n=("y", "size"))
    fig = go.Figure(go.Scatter(x=g["fitted"], y=g["resid"], mode="markers+lines", marker=dict(size=10, color=NAVY),
                               error_y=dict(type="data", array=1.96 * g["se"], color=TEAL, thickness=2),
                               text=[f"n={n}" for n in g["n"]], hovertemplate="%{text}<br>mean residual %{y:.3f}"
                                                                              "<extra></extra>"))
    fig.add_hline(y=0, line=dict(color=INK, width=1))
    fig.update_layout(title=sub(f"Binned residuals vs predicted probability — {res['best']}",
                                f"{_split_note(res)} · {len(g)} quantile bins · whiskers = ±1.96 SE · bins away from "
                                f"zero show where the model is systematically off"),
                      xaxis=dict(title="mean predicted probability in bin", range=[0, 1]),
                      yaxis_title="mean residual (actual − predicted)", height=420)
    return fig


def subgroup_error_chart(res: dict | None) -> go.Figure:
    """Error rate of the best model by role family of the squad member."""
    if not _fitted(res):
        return _empty(GATE_MSG, "Error by subgroup")
    g = res["subgroup"].sort_values("error_rate")
    fig = go.Figure(go.Bar(y=[f"{f} (n={n})" for f, n in zip(g["role_family"], g["n"])], x=g["error_rate"] * 100,
                           orientation="h", marker_color=[AMBER if n < 20 else NAVY for n in g["n"]],
                           text=[f"{v:.0%}" for v in g["error_rate"]], textposition="outside"))
    fig.update_layout(title=sub(f"Error rate by subgroup — {res['best']}",
                                f"{_split_note(res)} · share of rows where the top-11 prediction is wrong · amber = "
                                f"fewer than 20 rows · role comes from the position played that day, so unused bench "
                                f"players have none"),
                      xaxis=dict(title="% of rows misclassified", range=[0, 100]), height=380, margin=dict(l=260))
    return fig


def learning_curve_chart(res: dict | None) -> go.Figure:
    """Training and hold-out ROC-AUC as the number of training matches grows."""
    if not _fitted(res):
        return _empty(GATE_MSG, "Learning curve")
    lc = res["learning_curve"]
    if lc.empty:
        return _empty("Too few training matches for a learning curve.", "Learning curve")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=lc["train_matches"], y=lc["train_auc"], mode="lines+markers", name="training AUC",
                             line=dict(color=SLATE, width=2, dash="dash")))
    fig.add_trace(go.Scatter(x=lc["train_matches"], y=lc["holdout_auc"], mode="lines+markers", name="hold-out AUC",
                             line=dict(color=NAVY, width=3)))
    gap = float(lc["train_auc"].iloc[-1] - lc["holdout_auc"].iloc[-1])
    fig.update_layout(title=sub(f"Learning curve — {res['best']}",
                                f"model refitted on the first k matches, always scored on the same {_split_note(res)} · "
                                f"final train–test gap {gap:.3f} · a flat hold-out curve means more matches of the "
                                f"same kind add little"),
                      xaxis_title="training matches (chronological)", yaxis=dict(title="ROC-AUC", range=[0.4, 1.02]),
                      height=420, legend=dict(orientation="h", y=-0.2))
    return fig


def cv_distribution_chart(res: dict | None, metric: str = "f1") -> go.Figure:
    """Fold-by-fold scores of every model (each point is one time-ordered fold)."""
    if not _fitted(res):
        return _empty(GATE_MSG, "Cross-validation score distribution")
    cv = res["cv"].dropna(subset=[metric])
    fig = go.Figure()
    for m, g in cv.groupby("model"):
        fig.add_trace(go.Box(y=g[metric], name=m.replace("Baseline: ", "Baseline:<br>"), boxpoints="all", jitter=0.3,
                             pointpos=0, marker=dict(color=MODEL_COLORS.get(m, PURPLE), size=8),
                             line=dict(color=MODEL_COLORS.get(m, PURPLE)),
                             text=[f"fold {f}: {a} train / {b} test matches" for f, a, b in
                                   zip(g["fold"], g["train_matches"], g["test_matches"])],
                             hovertemplate="%{text}<br>%{y:.3f}<extra></extra>"))
    fig.update_layout(title=sub(f"Cross-validation {metric.replace('_', ' ')} by fold",
                                f"{cv['fold'].nunique()} expanding-window folds · with so few folds the boxes describe "
                                f"spread only; overlapping boxes mean the models are not distinguishable"),
                      yaxis_title=metric.replace("_", " "), height=420, showlegend=False)
    return fig


def scree_chart(pca: dict | None) -> go.Figure:
    """Explained variance per principal component with the cumulative curve."""
    if not pca:
        return _empty("Too few eligible players for a PCA.", "PCA scree plot")
    ev, cum = pca["explained"] * 100, pca["cumulative"] * 100
    k = np.arange(1, len(ev) + 1)
    fig = go.Figure()
    fig.add_bar(x=k, y=ev, name="component", marker_color=TEAL)
    fig.add_trace(go.Scatter(x=k, y=cum, mode="lines+markers", name="cumulative", line=dict(color=NAVY, width=2.5)))
    fig.add_hline(y=80, line=dict(color=MUTED, dash="dot"), annotation_text="80%")
    fig.update_layout(title=sub("PCA scree plot — player profiles",
                                f"n = {pca['n_players']} outfield players · {len(pca['metrics'])} standardised metrics · "
                                f"PC1 {ev[0]:.0f}%, PC2 {ev[1]:.0f}% · {pca['components_for_80pct']} components reach "
                                f"80%"),
                      xaxis=dict(title="principal component", dtick=1), yaxis=dict(title="% of variance",
                                                                                  range=[0, 105]),
                      height=420, legend=dict(orientation="h", y=-0.2))
    return fig


def loadings_heatmap(pca: dict | None) -> go.Figure:
    """Loadings of the first components on each metric."""
    if not pca:
        return _empty("Too few eligible players for a PCA.", "PCA loadings")
    ld = pca["loadings"]
    fig = heat(ld.to_numpy(float), list(ld.columns), list(ld.index), "", colorscale=DIV_SCALE, zmid=0,
               colorbar="loading")
    fig.update_layout(title=sub("PCA loadings — which metrics define each component",
                                f"n = {pca['n_players']} players · sign is arbitrary per component; read the contrast "
                                f"between positive and negative loadings"), margin=dict(l=200))
    return fig


def pca_map(pca: dict | None, highlight_team: str | None = None) -> go.Figure:
    """Players on the first two principal components, coloured by role family."""
    if not pca:
        return _empty("Too few eligible players for a PCA.", "PCA player map")
    f = pca["frame"]
    fig = go.Figure()
    for fam, g in f.groupby("role_family"):
        hl = g["team_name"] == highlight_team
        fig.add_trace(go.Scatter(x=g["pc1"], y=g["pc2"], mode="markers+text", name=f"{fam} (n={len(g)})",
                                 text=[p.split()[-1] if h else "" for p, h in zip(g["player_name"], hl)],
                                 textposition="top center", textfont=dict(size=9),
                                 marker=dict(size=[12 if h else 8 for h in hl], color=FAMILY_COLORS.get(fam, SLATE),
                                             opacity=0.85, line=dict(color=[INK if h else "white" for h in hl],
                                                                     width=[1.5 if h else 0.5 for h in hl])),
                                 hovertext=g["player_name"] + " · " + g["team_name"],
                                 hovertemplate="%{hovertext}<extra></extra>"))
    ev = pca["explained"] * 100
    fig.update_layout(title=sub("PCA player map",
                                f"n = {pca['n_players']} players · the two axes keep {ev[0] + ev[1]:.0f}% of the "
                                f"variance, so distances here are approximate"
                                + (f" · labelled and outlined = {highlight_team}" if highlight_team else "")),
                      xaxis_title=f"PC1 ({ev[0]:.0f}% of variance)", yaxis_title=f"PC2 ({ev[1]:.0f}% of variance)",
                      height=500, legend=dict(orientation="h", y=-0.2))
    return fig


def cluster_selection_chart(cl: dict | None) -> go.Figure:
    """Model-selection curves: inertia, silhouette, Calinski-Harabasz / Davies-Bouldin and GMM BIC by k."""
    if not cl:
        return _empty("Too few eligible players for clustering.", "Cluster model selection")
    s = cl["selection"]
    fig = make_subplots(rows=1, cols=4, subplot_titles=["Elbow: K-Means inertia", "Silhouette (higher = better)",
                                                        "Davies–Bouldin (lower = better)",
                                                        "Gaussian-mixture BIC (lower = better)"])
    fig.add_trace(go.Scatter(x=s["k"], y=s["inertia"], mode="lines+markers", line=dict(color=NAVY), showlegend=False),
                  1, 1)
    fig.add_trace(go.Scatter(x=s["k"], y=s["silhouette_kmeans"], mode="lines+markers", name="K-Means",
                             line=dict(color=NAVY)), 1, 2)
    fig.add_trace(go.Scatter(x=s["k"], y=s["silhouette_ward"], mode="lines+markers", name="Ward",
                             line=dict(color=TEAL, dash="dash")), 1, 2)
    fig.add_trace(go.Scatter(x=s["k"], y=s["davies_bouldin"], mode="lines+markers", line=dict(color=AMBER),
                             showlegend=False), 1, 3)
    fig.add_trace(go.Scatter(x=s["k"], y=s["gmm_bic"], mode="lines+markers", line=dict(color=PURPLE),
                             showlegend=False), 1, 4)
    fig.add_vline(x=cl["k_best"], line=dict(color=RED, dash="dot"), row=1, col=2)
    verdict = "weak structure (silhouette < 0.5: groups overlap)" if cl["silhouette_best"] < 0.5 else \
        "reasonable separation"
    agree = "criteria agree" if cl["k_bic"] == cl["k_best"] else \
        f"criteria disagree (BIC prefers k = {cl['k_bic']}) — a sign of continuous styles"
    fig.update_layout(title=sub("Cluster model selection",
                                f"n = {cl['n_players']} players · silhouette-best k = {cl['k_best']} "
                                f"({cl['silhouette_best']:.2f}) — {verdict} · {agree}"),
                      height=380, legend=dict(orientation="h", y=-0.25))
    fig.update_xaxes(title_text="k")
    return fig


def cluster_projection_chart(cl: dict | None) -> go.Figure:
    """The same players in PCA space, coloured by the labels of four clustering algorithms."""
    if not cl:
        return _empty("Too few eligible players for clustering.", "Cluster projection")
    f, names = cl["frame"], list(cl["labels"])
    titles = []
    for n in names:
        lab = cl["labels"][n]
        k, noise = len(set(lab) - {-1}), int((lab == -1).sum())
        titles.append(f"{n}: {k} cluster(s)" + (f", {noise} noise" if noise else ""))
    fig = make_subplots(rows=1, cols=4, subplot_titles=titles, shared_yaxes=True)
    pal = [NAVY, TEAL, AMBER, RED, PURPLE, SLATE] * 3
    for c, n in enumerate(names, 1):
        fig.add_trace(go.Scatter(x=f["pc1"], y=f["pc2"], mode="markers", showlegend=False,
                                 marker=dict(size=7, color=[pal[l] if l >= 0 else "#bbbbbb" for l in f[n]],
                                             line=dict(color="white", width=0.4)),
                                 hovertext=f["player_name"], hovertemplate="%{hovertext}<extra></extra>"), 1, c)
    fig.update_xaxes(title_text="PC1")
    fig.update_yaxes(title_text="PC2", row=1, col=1)
    fig.update_layout(title=sub("Four clustering algorithms on the same players",
                                f"n = {cl['n_players']} · partitioning methods use k = {cl['k_best']} · grey = DBSCAN "
                                f"noise (eps {cl['dbscan_eps']:.2f}, min 5 neighbours) · 2-D PCA projection of a "
                                f"{len(cl['metrics'])}-dimensional space"), height=400)
    return fig


def ari_heatmap(cl: dict | None) -> go.Figure:
    """Adjusted Rand index between the partitions of the four algorithms."""
    if not cl:
        return _empty("Too few eligible players for clustering.", "Clustering agreement")
    a = cl["ari"]
    fig = heat(a.to_numpy(float), list(a.columns), list(a.index), "", zmin=0, zmax=1, colorbar="ARI")
    fig.update_layout(title=sub("Agreement between clustering algorithms (adjusted Rand index)",
                                f"n = {cl['n_players']} players · 1 = identical partitions, 0 = chance-level agreement"),
                      height=420, xaxis=dict(tickangle=-25))
    return fig


def cluster_profile_chart(cl: dict | None) -> go.Figure:
    """Cluster sizes and the metrics that separate the K-Means clusters most (epsilon-squared)."""
    if not cl:
        return _empty("Too few eligible players for clustering.", "Cluster profiles")
    sizes = pd.Series(cl["labels"]["K-Means"]).value_counts().sort_index()
    eff = cl["effects"]
    fig = make_subplots(rows=1, cols=2, column_widths=[0.3, 0.7],
                        subplot_titles=["cluster sizes (K-Means)", "which metrics separate the clusters (ε²)"])
    fig.add_trace(go.Bar(x=[f"cluster {i}" for i in sizes.index], y=sizes.values, marker_color=COLORWAY[:len(sizes)],
                         text=sizes.values, textposition="outside", showlegend=False), 1, 1)
    fig.add_trace(go.Bar(y=eff["metric"], x=eff["epsilon2"], orientation="h", marker_color=TEAL, showlegend=False),
                  1, 2)
    fig.update_layout(title=sub("Cluster profiles",
                                f"k = {cl['k_best']} · separated mainly by {eff['metric'].iloc[-1]} and "
                                f"{eff['metric'].iloc[-2]} · ε² = Kruskal–Wallis effect size across clusters · clusters "
                                f"are a descriptive vocabulary, not fixed player types"), height=440)
    return fig


def stability_hist(stab: pd.DataFrame | None, k: int) -> go.Figure:
    """Bootstrap stability of the K-Means partition (ARI against the full-sample labels)."""
    msg = _missing(stab, ["ari"])
    if msg:
        return _empty(msg, "Cluster stability")
    fig = go.Figure(go.Histogram(x=stab["ari"], xbins=dict(start=0, end=1.0001, size=0.05), marker_color=TEAL))
    m = float(stab["ari"].mean())
    fig.add_vline(x=m, line=dict(color=NAVY, width=3), annotation_text=f"mean {m:.2f}")
    verdict = "stable" if m >= 0.8 else "moderately stable" if m >= 0.6 else "unstable"
    fig.update_layout(title=sub(f"Cluster stability under resampling (k = {k})",
                                f"{len(stab)} bootstrap refits · ARI between each refit and the full-sample partition · "
                                f"{verdict}: {'the grouping survives resampling' if m >= 0.8 else 'membership changes when players are resampled'}"),
                      xaxis=dict(title="adjusted Rand index", range=[0, 1.02]), yaxis_title="bootstrap refits",
                      height=380, bargap=0.05)
    return fig


def outlier_chart(scores: pd.DataFrame | None, top: int = 15) -> go.Figure:
    """Players with the most unusual statistical profiles (isolation-forest score)."""
    msg = _missing(scores, ["player_name", "team_name", "anomaly_score", "most_extreme_metric", "extreme_z"])
    if msg:
        return _empty(msg, "Profile outliers")
    d = scores.head(top).iloc[::-1]
    fig = go.Figure(go.Bar(y=d["player_name"] + " · " + d["team_name"].str[:12], x=d["anomaly_score"],
                           orientation="h", marker_color=PURPLE,
                           text=[f"{m} (z = {z:+.1f})" for m, z in zip(d["most_extreme_metric"], d["extreme_z"])],
                           textposition="outside", cliponaxis=False))
    fig.update_layout(title=sub("Most unusual player profiles",
                                f"top {len(d)} of {len(scores)} players · isolation-forest score (higher = easier to "
                                f"isolate) · label = the metric furthest from the sample mean · unusual means "
                                f"statistically distinctive, not better or worse"),
                      xaxis=dict(title="anomaly score", range=[d["anomaly_score"].min() * 0.9,
                                                               d["anomaly_score"].max() * 1.25]),
                      height=max(420, 28 * len(d) + 130), margin=dict(l=260, r=40))
    return fig
