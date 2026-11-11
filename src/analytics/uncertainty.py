"""Bootstrap confidence intervals and related uncertainty helpers."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def bootstrap_ci(values: np.ndarray, stat=np.mean, n_boot: int = 2000, seed: int = 0, alpha: float = 0.05):
    rng = np.random.default_rng(seed)
    v = np.asarray(values, dtype=float)
    boots = np.array([stat(rng.choice(v, len(v), replace=True)) for _ in range(n_boot)])
    return float(np.quantile(boots, alpha / 2)), float(np.quantile(boots, 1 - alpha / 2))


def bootstrap_distribution(values: Any, stat=np.mean, n_boot: int = 2000, seed: int = 0) -> np.ndarray:
    """Bootstrap replicates of ``stat`` (resampling the observations with replacement)."""
    v = np.asarray(values, dtype=float)
    v = v[~np.isnan(v)]
    if len(v) < 2:
        return np.array([])
    rng = np.random.default_rng(seed)
    return np.array([stat(rng.choice(v, len(v), replace=True)) for _ in range(n_boot)])


def bootstrap_rate_intervals(pms: pd.DataFrame, players: pd.DataFrame, numerator: str = "xg",
                             n_boot: int = 2000, seed: int = 0, alpha: float = 0.05) -> pd.DataFrame:
    """Per-90 rate with a bootstrap interval that resamples a player's *matches* (the independent unit).

    ``players`` holds one row per player with ``player_id``, ``team_id`` and ``player_name``. Events inside a
    match are not independent, so resampling events would understate the uncertainty.
    """
    rng = np.random.default_rng(seed)
    rows = []
    for r in players.itertuples():
        g = pms[(pms["player_id"] == r.player_id) & (pms["team_id"] == r.team_id)][[numerator, "minutes_played"]]
        g = g.dropna().to_numpy(float)
        g = g[g[:, 1] > 0]
        if len(g) < 3:
            continue
        rate = g[:, 0].sum() / g[:, 1].sum() * 90
        boots = []
        for _ in range(n_boot):
            i = rng.integers(0, len(g), len(g))
            boots.append(g[i, 0].sum() / g[i, 1].sum() * 90)
        rows.append({"player_id": r.player_id, "player": r.player_name, "rate_p90": rate,
                     "lo": float(np.quantile(boots, alpha / 2)), "hi": float(np.quantile(boots, 1 - alpha / 2)),
                     "matches": len(g), "minutes": float(g[:, 1].sum())})
    return pd.DataFrame(rows).sort_values("rate_p90").reset_index(drop=True) if rows else pd.DataFrame(
        columns=["player_id", "player", "rate_p90", "lo", "hi", "matches", "minutes"])


def wilson_interval(k: Any, n: Any, z: float = 1.96) -> tuple[np.ndarray, np.ndarray]:
    """Wilson score interval for a proportion k / n (well behaved for small n and extreme proportions)."""
    k, n = np.asarray(k, float), np.asarray(n, float)
    with np.errstate(divide="ignore", invalid="ignore"):
        p = k / n
        denom = 1 + z ** 2 / n
        centre = (p + z ** 2 / (2 * n)) / denom
        half = z * np.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / denom
    lo, hi = np.where(n > 0, centre - half, np.nan), np.where(n > 0, centre + half, np.nan)
    return np.clip(lo, 0, 1), np.clip(hi, 0, 1)


def shrunk_proportion(k: Any, n: Any, prior_mean: float, prior_strength: float = 10.0) -> np.ndarray:
    """Beta-binomial shrinkage of a proportion towards ``prior_mean``.

    ``prior_strength`` is the number of pseudo-observations: small samples move most of the way to the pooled
    value, large samples keep their own estimate. Used so that managers with a handful of matches are never
    ranked on raw proportions.
    """
    k, n = np.asarray(k, float), np.asarray(n, float)
    return (k + prior_mean * prior_strength) / (n + prior_strength)


def interval_width_by_sample(values: Any, sizes: list[int] | None = None, stat=np.mean, n_boot: int = 500,
                             seed: int = 0) -> pd.DataFrame:
    """Bootstrap interval of ``stat`` when only the first ``k`` observations are available (stability check)."""
    v = np.asarray(values, dtype=float)
    v = v[~np.isnan(v)]
    sizes = sizes or [k for k in (5, 8, 12, 17, 22, 28, 34, 50, 75, 100) if k <= len(v)]
    rows = []
    for k in sizes:
        sub = v[:k]
        b = bootstrap_distribution(sub, stat, n_boot, seed)
        if len(b):
            rows.append({"n": k, "estimate": float(stat(sub)), "lo": float(np.quantile(b, 0.025)),
                         "hi": float(np.quantile(b, 0.975))})
    out = pd.DataFrame(rows)
    if len(out):
        out["width"] = out["hi"] - out["lo"]
    return out
