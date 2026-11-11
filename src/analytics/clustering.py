"""Player archetype clustering."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy import stats as sps

from src.features.player_features import label


def player_archetypes(season_pct: pd.DataFrame, metrics: list[str], min_minutes: float, seed: int = 0,
                      k_range: range = range(3, 8)) -> dict | None:
    """Unsupervised player archetypes: standardise per-90 profiles, choose k by silhouette, project with PCA.

    Descriptive grouping of playing styles in this sample — not a quality ranking.
    """
    from sklearn.cluster import KMeans
    from sklearn.decomposition import PCA
    from sklearn.metrics import silhouette_score
    from sklearn.preprocessing import StandardScaler

    d = season_pct[(season_pct["minutes_played"] >= min_minutes) & (season_pct["primary_role"] != "GK")]
    d = d.dropna(subset=metrics).copy()
    if len(d) < 12:
        return None
    X = StandardScaler().fit_transform(d[metrics])
    scores = {}
    for k in k_range:
        if k < len(d):
            lab = KMeans(n_clusters=k, n_init=20, random_state=seed).fit_predict(X)
            scores[k] = silhouette_score(X, lab)
    k = max(scores, key=scores.get)
    km = KMeans(n_clusters=k, n_init=20, random_state=seed).fit(X)
    pca = PCA(n_components=2, random_state=seed).fit(X)
    pcs = pca.transform(X)
    centers = pd.DataFrame(km.cluster_centers_, columns=metrics)
    names = {}
    for c in range(k):
        top = centers.loc[c].sort_values(ascending=False).index[:2]
        names[c] = f"A{c + 1}: high {label(top[0])} & {label(top[1])}"
    d["pc1"], d["pc2"], d["cluster"] = pcs[:, 0], pcs[:, 1], km.labels_
    d["archetype"] = d["cluster"].map(names)
    centers.index = [names[c] for c in range(k)]
    return {"frame": d, "centers_z": centers, "k": k, "silhouette": scores, "explained": pca.explained_variance_ratio_,
            "loadings": pd.DataFrame(pca.components_.T, index=metrics, columns=["pc1", "pc2"])}


ARCHETYPE_METRICS = ["xg_p90", "xa_p90", "key_passes_p90", "progressive_passes_p90", "progressive_carries_p90",
                     "dribbles_completed_p90", "box_touches_p90", "pressures_p90", "tackles_won_p90",
                     "interceptions_p90", "clearances_p90", "aerials_won_p90", "ball_recoveries_p90",
                     "pass_completion_pct"]

MIN_PLAYERS_FOR_CLUSTERING = 20


def standardised_profiles(season_pct: pd.DataFrame, metrics: list[str], min_minutes: float
                          ) -> tuple[pd.DataFrame, np.ndarray] | None:
    """Eligible outfield players and their standardised metric matrix, or ``None`` when the sample is too small."""
    from sklearn.preprocessing import StandardScaler

    metrics = [m for m in metrics if m in season_pct.columns]
    d = season_pct[(season_pct["minutes_played"] >= min_minutes) & (season_pct["primary_role"] != "GK")]
    d = d.dropna(subset=metrics).reset_index(drop=True)
    if len(d) < MIN_PLAYERS_FOR_CLUSTERING or len(usable_metrics(d, metrics)) < 3:
        return None
    return d, StandardScaler().fit_transform(d[usable_metrics(d, metrics)])


def usable_metrics(d: pd.DataFrame, metrics: list[str]) -> list[str]:
    """Metrics that vary in the sample (a constant column carries no information and breaks rank tests)."""
    return [m for m in metrics if m in d.columns and d[m].nunique(dropna=True) > 1]


def pca_summary(season_pct: pd.DataFrame, metrics: list[str], min_minutes: float, seed: int = 0
                ) -> dict[str, Any] | None:
    """Explained variance, loadings and player scores of a PCA on standardised per-90 profiles."""
    from sklearn.decomposition import PCA

    metrics = [m for m in metrics if m in season_pct.columns]
    prep = standardised_profiles(season_pct, metrics, min_minutes)
    if prep is None:
        return None
    d, xs = prep
    metrics = usable_metrics(d, metrics)
    pca = PCA(random_state=seed).fit(xs)
    scores = pca.transform(xs)
    ratio = pca.explained_variance_ratio_
    n_show = min(4, len(metrics))
    loadings = pd.DataFrame(pca.components_[:n_show].T, index=[label(m) for m in metrics],
                            columns=[f"PC{i + 1}" for i in range(n_show)])
    frame = d[["player_id", "player_name", "team_name", "primary_role", "role_family", "minutes_played"]].copy()
    frame["pc1"], frame["pc2"] = scores[:, 0], scores[:, 1]
    return {"explained": ratio, "cumulative": np.cumsum(ratio), "loadings": loadings, "frame": frame,
            "components_for_80pct": int(np.argmax(np.cumsum(ratio) >= 0.8) + 1), "n_players": len(d),
            "metrics": metrics, "X": xs}


def clustering_comparison(season_pct: pd.DataFrame, metrics: list[str], min_minutes: float, seed: int = 0,
                          k_values: range = range(2, 11)) -> dict[str, Any] | None:
    """Model selection and algorithm agreement for K-Means, Ward, Gaussian mixture and DBSCAN.

    Returns the selection curves (inertia, silhouette, Calinski-Harabasz, Davies-Bouldin, GMM BIC), the labels
    of every algorithm at the silhouette-best k, their pairwise adjusted Rand index and a 2-D PCA projection.
    """
    from sklearn.cluster import DBSCAN, AgglomerativeClustering, KMeans
    from sklearn.decomposition import PCA
    from sklearn.metrics import (adjusted_rand_score, calinski_harabasz_score, davies_bouldin_score,
                                 silhouette_score)
    from sklearn.mixture import GaussianMixture
    from sklearn.neighbors import NearestNeighbors

    metrics = [m for m in metrics if m in season_pct.columns]
    prep = standardised_profiles(season_pct, metrics, min_minutes)
    if prep is None:
        return None
    d, xs = prep
    metrics = usable_metrics(d, metrics)
    ks = [k for k in k_values if k < len(d)]
    rows = []
    for k in ks:
        km = KMeans(k, n_init=20, random_state=seed).fit(xs)
        ward = AgglomerativeClustering(k, linkage="ward").fit_predict(xs)
        gmm = GaussianMixture(k, covariance_type="diag", random_state=seed, n_init=5).fit(xs)
        rows.append({"k": k, "inertia": km.inertia_, "silhouette_kmeans": silhouette_score(xs, km.labels_),
                     "silhouette_ward": silhouette_score(xs, ward),
                     "calinski_harabasz": calinski_harabasz_score(xs, km.labels_),
                     "davies_bouldin": davies_bouldin_score(xs, km.labels_), "gmm_bic": gmm.bic(xs)})
    sel = pd.DataFrame(rows)
    k_best = int(sel.loc[sel["silhouette_kmeans"].idxmax(), "k"])
    nn = np.sort(NearestNeighbors(n_neighbors=5).fit(xs).kneighbors(xs)[0][:, -1])
    eps = float(np.quantile(nn, 0.9))
    labels = {
        "K-Means": KMeans(k_best, n_init=20, random_state=seed).fit_predict(xs),
        "Agglomerative (Ward)": AgglomerativeClustering(k_best, linkage="ward").fit_predict(xs),
        "Gaussian mixture": GaussianMixture(k_best, covariance_type="diag", random_state=seed,
                                            n_init=5).fit(xs).predict(xs),
        "DBSCAN": DBSCAN(eps=eps, min_samples=5).fit_predict(xs),
    }
    ari = pd.DataFrame([[adjusted_rand_score(a, b) for b in labels.values()] for a in labels.values()],
                       index=list(labels), columns=list(labels))
    pcs = PCA(2, random_state=seed).fit_transform(xs)
    frame = d[["player_id", "player_name", "team_name", "primary_role", "role_family"]].copy()
    frame["pc1"], frame["pc2"] = pcs[:, 0], pcs[:, 1]
    for name, lab in labels.items():
        frame[name] = lab
    profile = d.assign(cluster=labels["K-Means"]).groupby("cluster")[metrics].mean()
    effects = []
    for m in metrics:
        groups = [d.loc[labels["K-Means"] == c, m] for c in sorted(set(labels["K-Means"]))]
        try:
            h = sps.kruskal(*groups).statistic
            eps2 = (h - len(groups) + 1) / (len(d) - len(groups))
        except ValueError:  # identical values in every cluster: no separation
            eps2 = 0.0
        effects.append({"metric": label(m), "epsilon2": eps2})
    return {"selection": sel, "k_best": k_best, "silhouette_best": float(sel["silhouette_kmeans"].max()),
            "k_bic": int(sel.loc[sel["gmm_bic"].idxmin(), "k"]), "knn_distance": nn, "dbscan_eps": eps,
            "labels": labels, "ari": ari, "frame": frame, "profile": profile,
            "effects": pd.DataFrame(effects).sort_values("epsilon2").reset_index(drop=True),
            "dbscan_noise": int((labels["DBSCAN"] == -1).sum()),
            "dbscan_clusters": len(set(labels["DBSCAN"]) - {-1}), "n_players": len(d), "metrics": metrics, "X": xs}


def cluster_stability(xs: np.ndarray, k: int, n_boot: int = 50, seed: int = 0) -> pd.DataFrame:
    """Adjusted Rand index between the full-sample K-Means partition and partitions fitted on bootstrap samples.

    Values near 1 mean the grouping survives resampling; values well below ~0.7 mean it should not be read as
    a set of fixed player types.
    """
    from sklearn.cluster import KMeans
    from sklearn.metrics import adjusted_rand_score

    rng = np.random.default_rng(seed)
    base = KMeans(k, n_init=10, random_state=seed).fit(xs)
    rows = []
    for b in range(n_boot):
        idx = rng.integers(0, len(xs), len(xs))
        km = KMeans(k, n_init=5, random_state=seed + b + 1).fit(xs[idx])
        rows.append({"replicate": b, "ari": adjusted_rand_score(base.labels_, km.predict(xs))})
    return pd.DataFrame(rows)


def outlier_scores(season_pct: pd.DataFrame, metrics: list[str], min_minutes: float, seed: int = 0
                   ) -> pd.DataFrame | None:
    """Isolation-forest anomaly score per player (higher = more unusual statistical profile, not better or worse)."""
    from sklearn.ensemble import IsolationForest

    metrics = [m for m in metrics if m in season_pct.columns]
    prep = standardised_profiles(season_pct, metrics, min_minutes)
    if prep is None:
        return None
    d, xs = prep
    metrics = usable_metrics(d, metrics)
    forest = IsolationForest(n_estimators=300, random_state=seed).fit(xs)
    out = d[["player_id", "player_name", "team_name", "primary_role", "role_family", "minutes_played"]].copy()
    out["anomaly_score"] = -forest.score_samples(xs)
    z = pd.DataFrame(xs, columns=metrics)
    out["most_extreme_metric"] = [label(m) for m in z.abs().idxmax(axis=1)]
    out["extreme_z"] = [float(z.loc[i, m]) for i, m in enumerate(z.abs().idxmax(axis=1))]
    return out.sort_values("anomaly_score", ascending=False).reset_index(drop=True)
