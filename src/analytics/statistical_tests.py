"""Correlation suites and group comparisons with effect sizes and FDR control."""
from __future__ import annotations

import numpy as np
from typing import Any
import pandas as pd
from scipy import stats as sps


def correlation_suite(df: pd.DataFrame, target: str, variables: list, n_boot: int = 2000, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for v in variables:
        d = df[[v, target]].dropna()
        x, y = d[v].to_numpy(float), d[target].to_numpy(float)
        pr, pp = sps.pearsonr(x, y)
        sr, sp_ = sps.spearmanr(x, y)
        kt, kp = sps.kendalltau(x, y)
        boots = []
        for _ in range(n_boot):
            i = rng.integers(0, len(d), len(d))
            if np.ptp(x[i]) > 0 and np.ptp(y[i]) > 0:
                boots.append(sps.spearmanr(x[i], y[i])[0])
        rows.append({"variable": v, "n": len(d), "pearson_r": pr, "pearson_p": pp, "spearman_rho": sr,
                     "spearman_p": sp_, "rho_ci_low": np.quantile(boots, 0.025), "rho_ci_high": np.quantile(boots, 0.975),
                     "kendall_tau": kt, "kendall_p": kp})
    out = pd.DataFrame(rows)
    out["spearman_q_BH"] = sps.false_discovery_control(out["spearman_p"].to_numpy())
    return out.sort_values("spearman_rho", key=np.abs, ascending=False).reset_index(drop=True)


def compare_groups(a, b, name_a: str, name_b: str, n_boot: int = 2000, seed: int = 0) -> dict:
    """Mann-Whitney U, Cliff's delta (from U) and a bootstrap CI for the difference in means."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    a, b = a[~np.isnan(a)], b[~np.isnan(b)]
    u, p = sps.mannwhitneyu(a, b, alternative="two-sided")
    delta = 2 * u / (len(a) * len(b)) - 1
    rng = np.random.default_rng(seed)
    diffs = [rng.choice(a, len(a)).mean() - rng.choice(b, len(b)).mean() for _ in range(n_boot)]
    mag = "negligible" if abs(delta) < 0.147 else "small" if abs(delta) < 0.33 else "medium" if abs(delta) < 0.474 else "large"
    return {"comparison": f"{name_a} vs {name_b}", "n_a": len(a), "n_b": len(b), "mean_a": a.mean(), "mean_b": b.mean(),
            "mean_diff": a.mean() - b.mean(), "diff_ci_low": np.quantile(diffs, 0.025), "diff_ci_high": np.quantile(diffs, 0.975),
            "test": "Mann-Whitney U (two-sided)", "statistic": u, "p_value": p, "effect": "Cliff's delta",
            "effect_size": delta, "magnitude": mag}


# ---------------------------------------------------------------------------
# Effect sizes, multiple testing and resampling tests
# ---------------------------------------------------------------------------
def _clean(a: Any) -> np.ndarray:
    a = np.asarray(a, float)
    return a[~np.isnan(a)]


def benjamini_hochberg(p_values: Any) -> np.ndarray:
    """Benjamini-Hochberg adjusted p-values (q-values); NaNs are passed through."""
    p = np.asarray(p_values, float)
    q = np.full_like(p, np.nan)
    ok = ~np.isnan(p)
    if ok.sum():
        q[ok] = sps.false_discovery_control(p[ok])
    return q


def effect_magnitude(delta: float) -> str:
    """Conventional labels for Cliff's delta (Romano et al. thresholds)."""
    d = abs(delta)
    return "negligible" if d < 0.147 else "small" if d < 0.33 else "medium" if d < 0.474 else "large"


def cliffs_delta(a: Any, b: Any) -> float:
    """Cliff's delta: P(a > b) - P(a < b). Rank-based, in [-1, 1]. NaN when either group is empty."""
    a, b = _clean(a), _clean(b)
    if not len(a) or not len(b):
        return float("nan")
    u = sps.mannwhitneyu(a, b, alternative="two-sided").statistic
    return float(2 * u / (len(a) * len(b)) - 1)


def hedges_g(a: Any, b: Any) -> float:
    """Hedges' g (bias-corrected standardised mean difference). Assumes roughly symmetric distributions."""
    a, b = _clean(a), _clean(b)
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return float("nan")
    sp = np.sqrt(((na - 1) * a.var(ddof=1) + (nb - 1) * b.var(ddof=1)) / (na + nb - 2))
    if sp == 0:
        return float("nan")
    return float((a.mean() - b.mean()) / sp * (1 - 3 / (4 * (na + nb) - 9)))


def correlation_matrix(df: pd.DataFrame, cols: list[str], method: str = "spearman"
                       ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Correlation matrix and the pairwise-complete sample size behind every cell."""
    if method not in ("pearson", "spearman", "kendall"):
        raise ValueError("method must be pearson, spearman or kendall")
    num = df[cols].apply(pd.to_numeric, errors="coerce")
    r = num.corr(method=method, min_periods=3)
    present = num.notna().astype(int)
    n = present.T.dot(present)
    return r, n


def pair_correlation(df: pd.DataFrame, x: str, y: str, n_boot: int = 2000, seed: int = 0) -> dict[str, Any]:
    """Pearson, Spearman and Kendall for one pair with a bootstrap interval for Spearman's rho."""
    d = df[[x, y]].apply(pd.to_numeric, errors="coerce").dropna()
    n = len(d)
    out: dict[str, Any] = {"x": x, "y": y, "n": n}
    if n < 4 or d[x].nunique() < 2 or d[y].nunique() < 2:
        out["status"] = "insufficient data (need at least 4 complete pairs with variation)"
        return out
    a, b = d[x].to_numpy(float), d[y].to_numpy(float)
    out["pearson_r"], out["pearson_p"] = map(float, sps.pearsonr(a, b))
    out["spearman_rho"], out["spearman_p"] = map(float, sps.spearmanr(a, b))
    out["kendall_tau"], out["kendall_p"] = map(float, sps.kendalltau(a, b))
    rng = np.random.default_rng(seed)
    boots = []
    for _ in range(n_boot):
        i = rng.integers(0, n, n)
        if np.ptp(a[i]) > 0 and np.ptp(b[i]) > 0:
            boots.append(sps.spearmanr(a[i], b[i])[0])
    out["rho_ci_low"], out["rho_ci_high"] = (float(np.quantile(boots, 0.025)), float(np.quantile(boots, 0.975))) \
        if boots else (np.nan, np.nan)
    out["boot"] = np.asarray(boots)
    slope, intercept = np.polyfit(a, b, 1)
    out["ols_slope"], out["ols_intercept"] = float(slope), float(intercept)
    out["status"] = "ok"
    return out


def partial_correlation(df: pd.DataFrame, x: str, y: str, covariates: list[str]) -> dict[str, Any]:
    """Spearman partial correlation: correlate rank residuals after regressing ranks on the covariates."""
    d = df[[x, y] + covariates].apply(pd.to_numeric, errors="coerce").dropna()
    n, k = len(d), len(covariates)
    if n < k + 5:
        return {"x": x, "y": y, "n": n, "status": f"insufficient data (n = {n}, covariates = {k})"}
    r = d.rank()
    z = np.column_stack([np.ones(n)] + [r[c].to_numpy(float) for c in covariates])
    res = {v: r[v].to_numpy(float) - z @ np.linalg.lstsq(z, r[v].to_numpy(float), rcond=None)[0] for v in (x, y)}
    pr = float(np.corrcoef(res[x], res[y])[0, 1])
    dof = n - 2 - k
    t = pr * np.sqrt(dof / max(1e-12, 1 - pr ** 2))
    raw = float(sps.spearmanr(d[x], d[y])[0])
    return {"x": x, "y": y, "n": n, "covariates": ", ".join(covariates), "raw_spearman": raw, "partial_spearman": pr,
            "p_value": float(2 * sps.t.sf(abs(t), dof)), "dof": dof, "status": "ok"}


def permutation_test(a: Any, b: Any, n_perm: int = 5000, seed: int = 0) -> dict[str, Any]:
    """Two-sided permutation test for a difference in means; returns the null distribution for plotting."""
    a, b = _clean(a), _clean(b)
    if len(a) < 2 or len(b) < 2:
        return {"status": "insufficient data", "n_a": len(a), "n_b": len(b)}
    rng = np.random.default_rng(seed)
    pooled = np.concatenate([a, b])
    obs = float(a.mean() - b.mean())
    null = np.empty(n_perm)
    for i in range(n_perm):
        perm = rng.permutation(pooled)
        null[i] = perm[:len(a)].mean() - perm[len(a):].mean()
    p = float((np.sum(np.abs(null) >= abs(obs)) + 1) / (n_perm + 1))
    return {"status": "ok", "observed": obs, "null": null, "p_value": p, "n_a": len(a), "n_b": len(b),
            "n_perm": n_perm}


def kruskal_groups(df: pd.DataFrame, value: str, group: str, min_n: int = 3) -> dict[str, Any]:
    """Kruskal-Wallis across groups with epsilon-squared; groups smaller than ``min_n`` are dropped and listed."""
    d = df[[value, group]].dropna()
    sizes = d.groupby(group)[value].size()
    keep = sizes[sizes >= min_n].index.tolist()
    groups = [d.loc[d[group] == g, value].to_numpy(float) for g in keep]
    out: dict[str, Any] = {"value": value, "group": group, "groups": keep, "sizes": sizes.to_dict(),
                           "dropped": sizes[sizes < min_n].index.tolist()}
    if len(groups) < 2:
        out["status"] = "insufficient data (fewer than two groups with enough observations)"
        return out
    h, p = sps.kruskal(*groups)
    n = sum(len(g) for g in groups)
    eps2 = (h - len(groups) + 1) / (n - len(groups))
    out.update(status="ok", H=float(h), p_value=float(p), epsilon2=float(eps2), n=n,
               magnitude="small" if eps2 < 0.08 else "medium" if eps2 < 0.26 else "large")
    return out


def pairwise_posthoc(df: pd.DataFrame, value: str, group: str, min_n: int = 3) -> pd.DataFrame:
    """Pairwise Mann-Whitney tests with Benjamini-Hochberg adjustment and Cliff's delta."""
    d = df[[value, group]].dropna()
    sizes = d.groupby(group)[value].size()
    keep = sizes[sizes >= min_n].index.tolist()
    rows = []
    for i, ga in enumerate(keep):
        for gb in keep[i + 1:]:
            a, b = d.loc[d[group] == ga, value], d.loc[d[group] == gb, value]
            u, p = sps.mannwhitneyu(a, b, alternative="two-sided")
            delta = 2 * u / (len(a) * len(b)) - 1
            rows.append({"group_a": ga, "group_b": gb, "n_a": len(a), "n_b": len(b), "median_a": a.median(),
                         "median_b": b.median(), "p_value": p, "cliffs_delta": delta,
                         "magnitude": effect_magnitude(delta)})
    out = pd.DataFrame(rows)
    if len(out):
        out["q_BH"] = benjamini_hochberg(out["p_value"])
    return out


def normality_table(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Shapiro-Wilk, skewness and excess kurtosis per column (guides the choice of rank-based methods)."""
    rows = []
    for c in cols:
        v = _clean(pd.to_numeric(df[c], errors="coerce"))
        if len(v) < 8 or np.ptp(v) == 0:
            rows.append({"variable": c, "n": len(v), "note": "too few or constant values"})
            continue
        w, p = sps.shapiro(v[:5000])
        rows.append({"variable": c, "n": len(v), "shapiro_W": w, "shapiro_p": p, "skew": sps.skew(v),
                     "excess_kurtosis": sps.kurtosis(v), "approximately_normal": bool(p >= 0.05)})
    return pd.DataFrame(rows)


def min_detectable_correlation(n: Any, alpha: float = 0.05, power: float = 0.8) -> np.ndarray:
    """Smallest |r| detectable with the given power in a two-sided test (Fisher z approximation)."""
    n = np.asarray(n, float)
    z = sps.norm.ppf(1 - alpha / 2) + sps.norm.ppf(power)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(n > 3, np.tanh(z / np.sqrt(n - 3)), np.nan)


def correlation_power(r: float, n: Any, alpha: float = 0.05) -> np.ndarray:
    """Approximate power to detect a true correlation ``r`` at sample size ``n`` (two-sided, Fisher z)."""
    n = np.asarray(n, float)
    with np.errstate(invalid="ignore", divide="ignore"):
        se = 1 / np.sqrt(n - 3)
        crit = sps.norm.ppf(1 - alpha / 2)
        mu = np.arctanh(r) / se
        return np.where(n > 3, sps.norm.sf(crit - mu) + sps.norm.cdf(-crit - mu), np.nan)


def autocorrelation(series: Any, max_lag: int = 10) -> pd.DataFrame:
    """Sample autocorrelation by lag with the approximate 95% white-noise bound (1.96 / sqrt(n))."""
    v = _clean(series)
    n = len(v)
    if n < 5:
        return pd.DataFrame(columns=["lag", "acf", "bound"])
    v = v - v.mean()
    denom = float((v ** 2).sum())
    lags = range(1, min(max_lag, n - 2) + 1)
    acf = [float((v[k:] * v[:-k]).sum() / denom) if denom else np.nan for k in lags]
    return pd.DataFrame({"lag": list(lags), "acf": acf, "bound": 1.96 / np.sqrt(n)})


def robust_comparison(df: pd.DataFrame, target: str, variables: list[str]) -> pd.DataFrame:
    """Pearson (outlier-sensitive) next to Spearman (rank-based) and the OLS vs Theil-Sen slope per variable."""
    rows = []
    for v in variables:
        d = df[[v, target]].apply(pd.to_numeric, errors="coerce").dropna()
        if len(d) < 5 or d[v].nunique() < 2:
            continue
        x, y = d[v].to_numpy(float), d[target].to_numpy(float)
        ts = sps.theilslopes(y, x)
        rows.append({"variable": v, "n": len(d), "pearson_r": sps.pearsonr(x, y)[0],
                     "spearman_rho": sps.spearmanr(x, y)[0], "ols_slope": np.polyfit(x, y, 1)[0],
                     "theil_sen_slope": ts[0]})
    out = pd.DataFrame(rows)
    if len(out):
        out["method_gap"] = (out["pearson_r"] - out["spearman_rho"]).abs()
    return out


def sample_sensitivity(season_pct: pd.DataFrame, x: str, y: str, thresholds: list[float] | None = None,
                       n_boot: int = 1000, seed: int = 0) -> pd.DataFrame:
    """How a player-level correlation moves as the minimum-minutes rule changes the analysed sample."""
    thresholds = thresholds or [0, 90, 180, 450, 900, 1350]
    rows = []
    for t in thresholds:
        d = season_pct[season_pct["minutes_played"] >= t]
        res = pair_correlation(d, x, y, n_boot=n_boot, seed=seed)
        rows.append({"min_minutes": t, "n": res["n"], "spearman_rho": res.get("spearman_rho", np.nan),
                     "rho_ci_low": res.get("rho_ci_low", np.nan), "rho_ci_high": res.get("rho_ci_high", np.nan)})
    return pd.DataFrame(rows)
