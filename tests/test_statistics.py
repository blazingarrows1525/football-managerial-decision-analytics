"""Statistical helpers against hand-calculable cases."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.analytics import descriptive as desc
from src.analytics import statistical_tests as stt
from src.analytics import uncertainty as unc


def test_cliffs_delta_extremes_and_symmetry():
    assert stt.cliffs_delta([5, 6, 7], [1, 2, 3]) == pytest.approx(1.0)
    assert stt.cliffs_delta([1, 2, 3], [5, 6, 7]) == pytest.approx(-1.0)
    assert stt.cliffs_delta([1, 2, 3], [1, 2, 3]) == pytest.approx(0.0)
    a, b = [1, 4, 6, 9], [2, 3, 7]
    assert stt.cliffs_delta(a, b) == pytest.approx(-stt.cliffs_delta(b, a))
    assert np.isnan(stt.cliffs_delta([], [1.0]))


def test_effect_magnitude_thresholds():
    assert [stt.effect_magnitude(d) for d in (0.1, -0.2, 0.4, -0.9)] == ["negligible", "small", "medium", "large"]


def test_hedges_g_sign_and_degenerate_cases():
    assert stt.hedges_g([2, 3, 4, 5], [0, 1, 2, 3]) > 0
    assert np.isnan(stt.hedges_g([1.0], [2.0, 3.0]))
    assert np.isnan(stt.hedges_g([1.0, 1.0], [1.0, 1.0]))


def test_benjamini_hochberg_known_values():
    q = stt.benjamini_hochberg([0.01, 0.04, 0.03, 0.20])
    assert q == pytest.approx([0.04, 0.0533333, 0.0533333, 0.20], rel=1e-4)
    assert np.isnan(stt.benjamini_hochberg([0.5, np.nan])[1])
    assert (stt.benjamini_hochberg([0.01, 0.02]) >= np.array([0.01, 0.02])).all()


def test_pair_correlation_perfect_and_insufficient():
    df = pd.DataFrame({"x": np.arange(12.0), "y": np.arange(12.0) * 2 + 1})
    res = stt.pair_correlation(df, "x", "y", n_boot=200)
    assert res["status"] == "ok" and res["n"] == 12
    assert res["pearson_r"] == pytest.approx(1.0) and res["spearman_rho"] == pytest.approx(1.0)
    assert res["ols_slope"] == pytest.approx(2.0) and res["ols_intercept"] == pytest.approx(1.0)
    few = stt.pair_correlation(df.head(3), "x", "y")
    assert few["status"].startswith("insufficient") and "pearson_r" not in few
    const = stt.pair_correlation(df.assign(y=1.0), "x", "y")
    assert const["status"].startswith("insufficient")


def test_pairwise_complete_n_is_reported():
    df = pd.DataFrame({"a": [1, 2, 3, 4, np.nan, 6.0], "b": [2, 1, 4, 3, 5, np.nan], "c": [1, 3, 2, 5, 4, 6.0]})
    r, n = stt.correlation_matrix(df, ["a", "b", "c"], "spearman")
    assert n.loc["a", "b"] == 4 and n.loc["a", "c"] == 5 and n.loc["c", "c"] == 6
    assert r.loc["a", "a"] == pytest.approx(1.0)
    with pytest.raises(ValueError):
        stt.correlation_matrix(df, ["a", "b"], "cosine")


def test_partial_correlation_removes_a_common_cause():
    rng = np.random.default_rng(1)
    z = rng.normal(size=300)
    df = pd.DataFrame({"z": z, "x": z + rng.normal(scale=0.3, size=300), "y": z + rng.normal(scale=0.3, size=300)})
    res = stt.partial_correlation(df, "x", "y", ["z"])
    assert res["status"] == "ok" and res["raw_spearman"] > 0.8 and abs(res["partial_spearman"]) < 0.2
    assert stt.partial_correlation(df.head(4), "x", "y", ["z"])["status"].startswith("insufficient")


def test_permutation_test_detects_and_does_not_invent():
    rng = np.random.default_rng(0)
    a, b = rng.normal(0, 1, 60), rng.normal(1.5, 1, 60)
    assert stt.permutation_test(a, b, n_perm=1000, seed=1)["p_value"] < 0.01
    same = stt.permutation_test(a, a.copy(), n_perm=500, seed=1)
    assert same["observed"] == pytest.approx(0.0) and same["p_value"] == pytest.approx(1.0)
    assert stt.permutation_test([1.0], [2.0, 3.0])["status"] == "insufficient data"
    r1, r2 = stt.permutation_test(a, b, 300, seed=7), stt.permutation_test(a, b, 300, seed=7)
    assert np.array_equal(r1["null"], r2["null"]), "resampling must be reproducible for a fixed seed"


def test_kruskal_and_posthoc():
    df = pd.DataFrame({"v": [1, 2, 3, 4, 11, 12, 13, 14, 21, 22, 23, 24.0, 5.0],
                       "g": ["a"] * 4 + ["b"] * 4 + ["c"] * 4 + ["tiny"]})
    kw = stt.kruskal_groups(df, "v", "g")
    assert kw["status"] == "ok" and kw["dropped"] == ["tiny"] and kw["groups"] == ["a", "b", "c"]
    assert kw["epsilon2"] > 0.8 and kw["magnitude"] == "large"
    post = stt.pairwise_posthoc(df, "v", "g")
    assert len(post) == 3 and (post["q_BH"] >= post["p_value"]).all() and (post["cliffs_delta"] == -1).all()
    one = stt.kruskal_groups(df[df["g"] == "a"], "v", "g")
    assert one["status"].startswith("insufficient")


def test_power_curves_are_monotonic():
    r = stt.min_detectable_correlation([10, 34, 100, 400])
    assert (np.diff(r) < 0).all() and 0.4 < r[1] < 0.5
    pw = stt.correlation_power(0.3, [10, 50, 200])
    assert (np.diff(pw) > 0).all() and 0 < pw[0] < pw[2] <= 1
    assert np.isnan(stt.min_detectable_correlation([3])[0])


def test_autocorrelation_of_a_trend_and_short_series():
    acf = stt.autocorrelation(np.arange(30.0), 5)
    assert acf["acf"].iloc[0] > 0.8 and acf["bound"].iloc[0] == pytest.approx(1.96 / np.sqrt(30))
    assert stt.autocorrelation([1.0, 2.0], 5).empty


def test_bootstrap_interval_contains_the_mean_and_is_reproducible():
    v = np.random.default_rng(3).normal(10, 2, 80)
    lo, hi = unc.bootstrap_ci(v, seed=5)
    assert lo < v.mean() < hi and (lo, hi) == unc.bootstrap_ci(v, seed=5)
    assert len(unc.bootstrap_distribution([1.0], n_boot=50)) == 0


def test_rate_intervals_resample_matches_not_events():
    pms = pd.DataFrame({"player_id": [1] * 6, "team_id": [9] * 6, "xg": [0.0, 0.5, 1.0, 0.0, 0.2, 0.3],
                        "minutes_played": [90.0] * 6})
    players = pd.DataFrame({"player_id": [1, 2], "team_id": [9, 9], "player_name": ["A", "B"]})
    out = unc.bootstrap_rate_intervals(pms, players, "xg", n_boot=300, seed=0)
    assert list(out["player"]) == ["A"], "a player without matches must be left out, not given a made-up interval"
    r = out.iloc[0]
    assert r["rate_p90"] == pytest.approx(2.0 / 540 * 90) and r["lo"] <= r["rate_p90"] <= r["hi"]
    assert r["matches"] == 6


def test_wilson_interval_and_shrinkage():
    lo, hi = unc.wilson_interval([0, 5, 10], [10, 10, 10])
    assert lo[0] == pytest.approx(0.0) and 0.25 < hi[0] < 0.35
    assert lo[1] < 0.5 < hi[1] and hi[2] == pytest.approx(1.0)
    assert np.isnan(unc.wilson_interval([0], [0])[0][0])
    shr = unc.shrunk_proportion([2, 200], [2, 200], prior_mean=0.5, prior_strength=20)
    assert 0.5 < shr[0] < 0.6 and shr[1] > 0.95, "small samples move to the prior, large ones keep their value"


def test_concentration_and_gini():
    c = desc.concentration(pd.Series({"a": 6.0, "b": 3.0, "c": 1.0, "d": 0.0}))
    assert list(c["label"]) == ["a", "b", "c"] and c["cumulative_share"].iloc[-1] == pytest.approx(1.0)
    assert c["share"].iloc[0] == pytest.approx(0.6)
    assert desc.gini([1, 1, 1, 1]) == pytest.approx(0.0)
    assert desc.gini([0, 0, 0, 10]) == pytest.approx(0.75)
    assert np.isnan(desc.gini([]))


def test_zone_table_counts_every_located_event():
    ev = pd.DataFrame({"x": [0.0, 119.9, 60.0, np.nan], "y": [0.0, 79.9, 40.0, 10.0]})
    z = desc.zone_table(ev, 3, 3)
    assert z.values.sum() == 3 and z.iloc[0, 0] == 1 and z.iloc[2, 2] == 1 and z.iloc[1, 1] == 1
