"""Statistical-inference charts added in V3 (catalogue family J).

Every chart states the sample size and the unit of analysis. Correlations and group differences shown here are
associations in one team-season; none of them is a causal estimate.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.visualization.distribution import nice
from src.visualization.theme import (AMBER, COLORWAY, DIV_SCALE, GRID, INK, MUTED, NAVY, RED, SLATE, TEAL, _empty, _missing, heat, low_sample, sub)


def correlation_matrix_chart(r: pd.DataFrame | None, n: pd.DataFrame | None, method: str, scope: str) -> go.Figure:
    """Correlation matrix with the pairwise-complete n in the hover text."""
    if r is None or r.empty:
        return _empty("No numeric columns to correlate.", f"{method.title()} correlation matrix")
    labels = [nice(c) for c in r.columns]
    fig = go.Figure(go.Heatmap(z=r.to_numpy(float), x=labels, y=labels, colorscale=DIV_SCALE, zmid=0, zmin=-1, zmax=1,
                               text=np.round(r.to_numpy(float), 2), texttemplate="%{text}", textfont=dict(size=9),
                               customdata=n.to_numpy() if n is not None else None, xgap=1, ygap=1,
                               colorbar=dict(title="r", thickness=12),
                               hovertemplate="%{y} × %{x}<br>r = %{z:.2f} · n = %{customdata}<extra></extra>"))
    nmin = int(n.to_numpy().min()) if n is not None else 0
    nmax = int(n.to_numpy().max()) if n is not None else 0
    fig.update_layout(title=sub(f"{method.title()} correlation matrix",
                                f"{scope} · pairwise-complete n from {nmin} to {nmax} (hover for each cell) · "
                                f"correlation is not causation" + low_sample(nmin, 20)),
                      height=max(480, 34 * len(labels) + 170), xaxis=dict(tickangle=-45),
                      yaxis=dict(autorange="reversed"), margin=dict(l=170))
    return fig


def forest_chart(corr: pd.DataFrame | None, target: str, scope: str) -> go.Figure:
    """Spearman correlations with bootstrap intervals, coloured by significance after FDR control."""
    msg = _missing(corr, ["variable", "spearman_rho", "rho_ci_low", "rho_ci_high", "spearman_q_BH", "n"])
    if msg:
        return _empty(msg, "Correlation forest plot")
    d = corr.iloc[::-1]
    sig = d["spearman_q_BH"] < 0.05
    fig = go.Figure(go.Scatter(x=d["spearman_rho"], y=[f"{nice(v)} (q = {q:.3f})" for v, q in
                                                        zip(d["variable"], d["spearman_q_BH"])],
                               mode="markers", marker=dict(size=11, color=[TEAL if s else SLATE for s in sig]),
                               error_x=dict(type="data", symmetric=False, array=d["rho_ci_high"] - d["spearman_rho"],
                                            arrayminus=d["spearman_rho"] - d["rho_ci_low"], color=GRID, thickness=5,
                                            width=0), hovertemplate="%{y}<br>ρ = %{x:.2f}<extra></extra>"))
    fig.add_vline(x=0, line=dict(color=INK, width=1))
    fig.update_layout(title=sub(f"Association with {nice(target)}: Spearman ρ and 95% bootstrap interval",
                                f"{scope} · n = {int(d['n'].iloc[0])} · {int(sig.sum())} of {len(d)} variables with "
                                f"q < 0.05 after Benjamini–Hochberg (teal) · intervals from 2,000 resamples of the "
                                f"unit of analysis"),
                      xaxis=dict(title="Spearman ρ", range=[-1, 1]), height=max(420, 32 * len(d) + 140),
                      margin=dict(l=270))
    return fig


def regression_scatter(df: pd.DataFrame | None, x: str, y: str, res: dict | None, scope: str,
                       hover: str | None = None, lowess: bool = False) -> go.Figure:
    """Scatter with an OLS line and a residual panel; reports three coefficients and the pairwise n."""
    title = f"{nice(y)} vs {nice(x)}"
    msg = _missing(df, [x, y])
    if msg:
        return _empty(msg, title)
    d = df[[x, y] + ([hover] if hover and hover in df.columns else [])].dropna(subset=[x, y])
    if res is None or res.get("status") != "ok":
        return _empty((res or {}).get("status", "Insufficient data for this pair."), title)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.72, 0.28], vertical_spacing=0.06)
    fig.add_trace(go.Scatter(x=d[x], y=d[y], mode="markers", name="observations",
                             marker=dict(color=NAVY, size=8, opacity=0.7, line=dict(color="white", width=0.6)),
                             text=d[hover] if hover and hover in d else None,
                             hovertemplate=("%{text}<br>" if hover and hover in d else "") + "%{x:.2f}, %{y:.2f}"
                                           "<extra></extra>"), 1, 1)
    xs = np.linspace(d[x].min(), d[x].max(), 60)
    fit = res["ols_slope"] * xs + res["ols_intercept"]
    fig.add_trace(go.Scatter(x=xs, y=fit, mode="lines", name="OLS line", line=dict(color=RED, width=2)), 1, 1)
    extra = ""
    if lowess:
        try:
            from statsmodels.nonparametric.smoothers_lowess import lowess as _lowess

            sm = _lowess(d[y].to_numpy(float), d[x].to_numpy(float), frac=0.6)
            fig.add_trace(go.Scatter(x=sm[:, 0], y=sm[:, 1], mode="lines", name="LOESS (span 0.6)",
                                     line=dict(color=AMBER, width=2, dash="dash")), 1, 1)
        except ImportError:
            extra = " · LOESS needs the optional statsmodels package (not installed)"
    resid = d[y] - (res["ols_slope"] * d[x] + res["ols_intercept"])
    fig.add_trace(go.Scatter(x=d[x], y=resid, mode="markers", showlegend=False,
                             marker=dict(color=SLATE, size=6, opacity=0.7)), 2, 1)
    fig.add_hline(y=0, line=dict(color=INK, width=1), row=2, col=1)
    fig.update_xaxes(title_text=nice(x), row=2, col=1)
    fig.update_yaxes(title_text=nice(y), row=1, col=1)
    fig.update_yaxes(title_text="residual", row=2, col=1)
    fig.update_layout(title=sub(title, f"{scope} · n = {res['n']} complete pairs · Pearson r = {res['pearson_r']:.2f}, "
                                       f"Spearman ρ = {res['spearman_rho']:.2f} (95% CI {res['rho_ci_low']:.2f} to "
                                       f"{res['rho_ci_high']:.2f}), Kendall τ = {res['kendall_tau']:.2f} · association, "
                                       f"not causation{extra}" + low_sample(res["n"], 20)),
                      height=560, legend=dict(orientation="h", y=1.06))
    return fig


def partial_chart(rows: list[dict] | None, scope: str) -> go.Figure:
    """Raw against partial Spearman correlation for each variable, given the stated covariates."""
    ok = [r for r in rows or [] if r.get("status") == "ok"]
    if not ok:
        return _empty("Partial correlations could not be computed (too few complete rows).", "Partial correlation")
    d = pd.DataFrame(ok)
    lab = [nice(v) for v in d["x"]]
    fig = go.Figure()
    fig.add_bar(y=lab, x=d["raw_spearman"], orientation="h", name="raw Spearman ρ", marker_color=SLATE)
    fig.add_bar(y=lab, x=d["partial_spearman"], orientation="h", name=f"partial (given {d['covariates'].iloc[0]})",
                marker_color=NAVY)
    fig.add_vline(x=0, line=dict(color=INK, width=1))
    fig.update_layout(barmode="group", title=sub(f"Raw vs partial correlation with {nice(d['y'].iloc[0])}",
                                                 f"{scope} · n = {int(d['n'].iloc[0])} · rank-based partial "
                                                 f"correlation · adjusting for an observed covariate does not remove "
                                                 f"unobserved confounding"),
                      xaxis=dict(title="Spearman ρ", range=[-1, 1]), height=max(380, 44 * len(d) + 140),
                      margin=dict(l=200), legend=dict(orientation="h", y=1.07))
    return fig


def bootstrap_hist(boot: Any, observed: float, title: str, x_title: str, scope: str) -> go.Figure:
    """Histogram of bootstrap replicates with the estimate and the percentile interval marked."""
    b = np.asarray(boot if boot is not None else [], float)
    if len(b) < 50:
        return _empty("Too few valid bootstrap replicates.", title)
    lo, hi = np.quantile(b, [0.025, 0.975])
    fig = go.Figure(go.Histogram(x=b, nbinsx=50, marker_color=TEAL, opacity=0.85))
    fig.add_vrect(x0=lo, x1=hi, fillcolor=AMBER, opacity=0.12, line_width=0)
    fig.add_vline(x=observed, line=dict(color=NAVY, width=3), annotation_text=f"estimate {observed:.2f}")
    fig.update_layout(title=sub(title, f"{scope} · {len(b):,} bootstrap replicates · shaded = 95% percentile interval "
                                       f"({lo:.2f} to {hi:.2f})"),
                      xaxis_title=x_title, yaxis_title="replicates", height=400, bargap=0.02)
    return fig


def permutation_chart(res: dict | None, name_a: str, name_b: str, value_label: str) -> go.Figure:
    """Null distribution of a difference in means under label permutation, with the observed difference."""
    title = "Permutation test"
    if not res or res.get("status") != "ok":
        return _empty("Too few observations in one of the groups for a permutation test.", title)
    null = res["null"]
    fig = go.Figure(go.Histogram(x=null, nbinsx=60, marker_color=SLATE, opacity=0.85, name="null differences"))
    fig.add_vline(x=res["observed"], line=dict(color=RED, width=3),
                  annotation_text=f"observed {res['observed']:+.2f}")
    fig.add_vline(x=-res["observed"], line=dict(color=RED, width=1, dash="dot"))
    fig.update_layout(title=sub(f"Permutation test: {name_a} vs {name_b}",
                                f"difference in mean {value_label} · n = {res['n_a']} vs {res['n_b']} · "
                                f"{res['n_perm']:,} random relabellings · two-sided p = {res['p_value']:.3f} · the grey "
                                f"histogram is what chance alone produces" + low_sample(min(res["n_a"], res["n_b"]), 10)),
                      xaxis_title=f"difference in mean {value_label} under the null", yaxis_title="permutations",
                      height=400, bargap=0.02, showlegend=False)
    return fig


def effect_size_chart(rows: list[dict] | None) -> go.Figure:
    """Cliff's delta of several two-group comparisons with conventional magnitude bands."""
    if not rows:
        return _empty("No comparisons available.", "Effect sizes")
    d = pd.DataFrame(rows).iloc[::-1]
    lab = [f"{c} (n {a}/{b}, p = {p:.3f})" for c, a, b, p in zip(d["comparison"], d["n_a"], d["n_b"], d["p_value"])]
    fig = go.Figure()
    for lo, hi, c in ((-0.147, 0.147, "rgba(141,153,174,0.20)"), (-0.33, -0.147, "rgba(233,162,59,0.12)"),
                      (0.147, 0.33, "rgba(233,162,59,0.12)")):
        fig.add_vrect(x0=lo, x1=hi, fillcolor=c, line_width=0)
    fig.add_trace(go.Scatter(x=d["effect_size"], y=lab, mode="markers+text", text=d["magnitude"],
                             textposition="middle right", marker=dict(size=13, color=NAVY)))
    fig.add_vline(x=0, line=dict(color=INK, width=1))
    fig.update_layout(title=sub("Effect sizes of group comparisons (Cliff's δ)",
                                "δ = P(first group higher) − P(second higher), from the Mann–Whitney U · grey band = "
                                "negligible (|δ| < 0.147), amber = small (< 0.33) · p-values are unadjusted"),
                      xaxis=dict(title="Cliff's δ", range=[-1, 1]), height=max(340, 60 * len(d) + 140),
                      margin=dict(l=380))
    return fig


def posthoc_heatmap(post: pd.DataFrame | None, kw: dict | None, value: str, group: str) -> go.Figure:
    """Pairwise post-hoc comparisons: BH-adjusted q-values with Cliff's delta in the hover."""
    title = f"Post-hoc comparisons of {nice(value)} by {group.replace('_', ' ')}"
    msg = _missing(post, ["group_a", "group_b", "q_BH", "cliffs_delta"])
    if msg or not kw or kw.get("status") != "ok":
        return _empty(msg or (kw or {}).get("status", "Insufficient data."), title)
    groups = sorted(set(post["group_a"]) | set(post["group_b"]))
    q = pd.DataFrame(np.nan, index=groups, columns=groups)
    dl = q.copy()
    for r in post.itertuples():
        q.loc[r.group_a, r.group_b] = q.loc[r.group_b, r.group_a] = r.q_BH
        dl.loc[r.group_a, r.group_b] = r.cliffs_delta
        dl.loc[r.group_b, r.group_a] = -r.cliffs_delta
    fig = go.Figure(go.Heatmap(z=q.to_numpy(float), x=groups, y=groups, colorscale=[[0, NAVY], [0.05, TEAL],
                                                                                     [0.2, "#e9eef0"], [1, "#f7f5f0"]],
                               zmin=0, zmax=1, text=np.round(q.to_numpy(float), 3), texttemplate="%{text}",
                               customdata=dl.to_numpy(float), xgap=2, ygap=2, colorbar=dict(title="q (BH)", thickness=12),
                               hovertemplate="%{y} vs %{x}<br>q = %{z:.3f} · Cliff's δ = %{customdata:.2f}"
                                             "<extra></extra>"))
    fig.update_layout(title=sub(title, f"Kruskal–Wallis H = {kw['H']:.1f}, p = {kw['p_value']:.3f}, ε² = "
                                       f"{kw['epsilon2']:.2f} ({kw['magnitude']}) · n = {kw['n']} in {len(kw['groups'])} "
                                       f"groups · cells = pairwise Mann–Whitney q after Benjamini–Hochberg"
                                + (f" · dropped (< 3): {', '.join(map(str, kw['dropped']))}" if kw["dropped"] else "")),
                      height=max(420, 40 * len(groups) + 170), yaxis=dict(autorange="reversed"))
    return fig


def pvalue_adjust_chart(corr: pd.DataFrame | None, scope: str) -> go.Figure:
    """Raw p-values next to Benjamini-Hochberg q-values for a family of tests."""
    msg = _missing(corr, ["variable", "spearman_p", "spearman_q_BH"])
    if msg:
        return _empty(msg, "Multiple-testing adjustment")
    d = corr.sort_values("spearman_p")
    lab = [nice(v) for v in d["variable"]]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=lab, y=d["spearman_p"], mode="lines+markers", name="raw p-value",
                             line=dict(color=SLATE, width=2)))
    fig.add_trace(go.Scatter(x=lab, y=d["spearman_q_BH"], mode="lines+markers", name="BH-adjusted q-value",
                             line=dict(color=NAVY, width=2)))
    fig.add_hline(y=0.05, line=dict(color=RED, dash="dash"), annotation_text="0.05")
    raw, adj = int((d["spearman_p"] < 0.05).sum()), int((d["spearman_q_BH"] < 0.05).sum())
    fig.update_layout(title=sub("Multiple-testing adjustment",
                                f"{scope} · {len(d)} tests in the family · {raw} below 0.05 before adjustment, {adj} "
                                f"after Benjamini–Hochberg (false-discovery control)"),
                      yaxis=dict(title="p / q value", type="log"), xaxis=dict(tickangle=-40), height=440,
                      legend=dict(orientation="h", y=1.07))
    return fig


def power_curve_chart(n_obs: int, effects: tuple[float, ...] = (0.2, 0.3, 0.43, 0.5)) -> go.Figure:
    """Power to detect a true correlation as the sample grows, with the current sample marked."""
    from src.analytics.statistical_tests import correlation_power, min_detectable_correlation

    ns = np.arange(8, 401)
    fig = go.Figure()
    for i, r in enumerate(effects):
        fig.add_trace(go.Scatter(x=ns, y=correlation_power(r, ns), mode="lines", name=f"true |r| = {r:.2f}",
                                 line=dict(color=COLORWAY[i % len(COLORWAY)], width=2.5)))
    fig.add_hline(y=0.8, line=dict(color=MUTED, dash="dot"), annotation_text="80% power")
    fig.add_vline(x=n_obs, line=dict(color=RED, width=2), annotation_text=f"this study: n = {n_obs}")
    mdr = float(min_detectable_correlation(n_obs))
    fig.update_layout(title=sub("Statistical power for a correlation test",
                                f"two-sided α = 0.05, Fisher z approximation · with n = {n_obs} only |r| ≥ {mdr:.2f} is "
                                f"detectable with 80% power — smaller true associations will usually be missed"),
                      xaxis=dict(title="sample size (independent units)", type="log"),
                      yaxis=dict(title="power", range=[0, 1.02], tickformat=".0%"), height=440)
    return fig


def sensitivity_chart(sens: pd.DataFrame | None, x: str, y: str) -> go.Figure:
    """A player-level correlation recomputed under different minimum-minutes rules."""
    msg = _missing(sens, ["min_minutes", "n", "spearman_rho", "rho_ci_low", "rho_ci_high"])
    if msg:
        return _empty(msg, "Sample-definition sensitivity")
    d = sens.dropna(subset=["spearman_rho"])
    if d.empty:
        return _empty("No threshold leaves enough players.", "Sample-definition sensitivity")
    lab = [f"≥ {int(m)} min<br>n = {int(n)}" for m, n in zip(d["min_minutes"], d["n"])]
    fig = go.Figure(go.Scatter(x=lab, y=d["spearman_rho"], mode="lines+markers", line=dict(color=NAVY, width=2),
                               marker=dict(size=10),
                               error_y=dict(type="data", symmetric=False, array=d["rho_ci_high"] - d["spearman_rho"],
                                            arrayminus=d["spearman_rho"] - d["rho_ci_low"], color=TEAL, thickness=3)))
    fig.add_hline(y=0, line=dict(color=INK, width=1))
    fig.update_layout(title=sub(f"Sensitivity of ρ({nice(x)}, {nice(y)}) to the minutes threshold",
                                "players excluded by the threshold are missing-by-rule, not at random · a result that "
                                "flips sign or loses its interval across thresholds depends on the inclusion rule"),
                      yaxis=dict(title="Spearman ρ (95% bootstrap CI)", range=[-1, 1]),
                      xaxis_title="minimum minutes played", height=440)
    return fig


def robust_chart(rob: pd.DataFrame | None, target: str, scope: str) -> go.Figure:
    """Pearson (outlier-sensitive) next to Spearman (rank-based) for each variable."""
    msg = _missing(rob, ["variable", "pearson_r", "spearman_rho", "method_gap"])
    if msg:
        return _empty(msg, "Robust vs classical estimates")
    d = rob.sort_values("method_gap")
    lab = [nice(v) for v in d["variable"]]
    fig = go.Figure()
    for a, b, y in zip(d["pearson_r"], d["spearman_rho"], lab):
        fig.add_trace(go.Scatter(x=[a, b], y=[y, y], mode="lines", line=dict(color=GRID, width=4), showlegend=False,
                                 hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=d["pearson_r"], y=lab, mode="markers", name="Pearson r",
                             marker=dict(size=11, color=AMBER)))
    fig.add_trace(go.Scatter(x=d["spearman_rho"], y=lab, mode="markers", name="Spearman ρ",
                             marker=dict(size=11, color=NAVY)))
    fig.add_vline(x=0, line=dict(color=INK, width=1))
    worst = d.iloc[-1]
    fig.update_layout(title=sub(f"Robust vs classical association with {nice(target)}",
                                f"{scope} · largest gap: {nice(worst['variable'])} ({worst['method_gap']:.2f}) · a "
                                f"large gap signals outliers or a non-linear relation"),
                      xaxis=dict(title="correlation coefficient", range=[-1, 1]),
                      height=max(400, 30 * len(d) + 140), margin=dict(l=200), legend=dict(orientation="h", y=1.07))
    return fig


def acf_chart(series: pd.DataFrame | None, acf: pd.DataFrame | None, metric: str, team: str) -> go.Figure:
    """Match-by-match series with its rolling mean, and the autocorrelation by lag."""
    title = f"{team}: trend and autocorrelation of {nice(metric)}"
    msg = _missing(series, ["match_date", metric]) or _missing(acf, ["lag", "acf", "bound"])
    if msg:
        return _empty(msg, title)
    fig = make_subplots(rows=1, cols=2, column_widths=[0.6, 0.4],
                        subplot_titles=["series (line = 5-match rolling mean)", "autocorrelation by lag"])
    s = series.sort_values("match_date")
    fig.add_trace(go.Scatter(x=s["match_date"], y=s[metric], mode="markers", marker=dict(color=SLATE, size=7),
                             showlegend=False), 1, 1)
    fig.add_trace(go.Scatter(x=s["match_date"], y=s[metric].rolling(5, min_periods=3).mean(), mode="lines",
                             line=dict(color=NAVY, width=2.5), showlegend=False), 1, 1)
    b = float(acf["bound"].iloc[0])
    fig.add_trace(go.Bar(x=acf["lag"], y=acf["acf"], marker_color=[RED if abs(v) > b else TEAL for v in acf["acf"]],
                         showlegend=False), 1, 2)
    fig.add_hline(y=b, line=dict(color=MUTED, dash="dot"), row=1, col=2)
    fig.add_hline(y=-b, line=dict(color=MUTED, dash="dot"), row=1, col=2)
    out = int((acf["acf"].abs() > b).sum())
    fig.update_layout(title=sub(title, f"n = {len(s)} matches · dotted = ±1.96/√n white-noise bound · {out} of "
                                       f"{len(acf)} lags outside it — with {len(acf)} lags about "
                                       f"{0.05 * len(acf):.1f} would cross by chance"), height=420)
    return fig


def stability_chart(stab: pd.DataFrame | None, title: str, y_title: str) -> go.Figure:
    """Estimate and bootstrap interval as more matches become available."""
    msg = _missing(stab, ["n", "estimate", "lo", "hi"])
    if msg:
        return _empty(msg, title)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=list(stab["n"]) + list(stab["n"][::-1]), y=list(stab["hi"]) + list(stab["lo"][::-1]),
                             fill="toself", fillcolor="rgba(42,157,143,0.18)", line=dict(width=0),
                             name="95% bootstrap interval", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=stab["n"], y=stab["estimate"], mode="lines+markers", name="estimate",
                             line=dict(color=NAVY, width=2.5)))
    fig.update_layout(title=sub(title, f"estimate using the first n matches in date order · interval width falls from "
                                       f"{stab['width'].iloc[0]:.2f} at n = {int(stab['n'].iloc[0])} to "
                                       f"{stab['width'].iloc[-1]:.2f} at n = {int(stab['n'].iloc[-1])}"),
                      xaxis_title="matches included", yaxis_title=y_title, height=420,
                      legend=dict(orientation="h", y=-0.2))
    return fig


def method_agreement_heatmap(corr: pd.DataFrame | None, target: str, scope: str) -> go.Figure:
    """Pearson, Spearman and Kendall side by side for each variable."""
    msg = _missing(corr, ["variable", "pearson_r", "spearman_rho", "kendall_tau"])
    if msg:
        return _empty(msg, "Correlation methods compared")
    m = corr.set_index("variable")[["pearson_r", "spearman_rho", "kendall_tau"]]
    fig = heat(m.to_numpy(float), ["Pearson r", "Spearman ρ", "Kendall τ"], [nice(v) for v in m.index], "",
               colorscale=DIV_SCALE, zmid=0, zmin=-1, zmax=1, colorbar="coefficient")
    agree = bool((np.sign(m).nunique(axis=1) == 1).all())
    fig.update_layout(title=sub(f"Three correlation methods against {nice(target)}",
                                f"{scope} · signs {'agree for every variable' if agree else 'DISAGREE for some variables'}"
                                f" · Kendall's τ is smaller in magnitude by construction"), margin=dict(l=200))
    return fig
