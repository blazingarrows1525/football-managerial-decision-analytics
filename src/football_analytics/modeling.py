"""Optional, data-gated modelling: who starts? (observed selection behaviour).

Prediction unit : player in a team's matchday squad for a match.
Target          : ``is_starter`` (1 = named in the Starting XI).
Prediction time : before kick-off.
Features        : only quantities computed from EARLIER matches (workload proxies,
                  start share, continuity, season-to-date minutes share, role).
Split           : chronological by match date (first 70% of team matches -> train).
Baseline        : "started the team's previous match".

This models what the coaching staff DID, not what was optimal. A model is fitted
only if the sample gate passes; otherwise the notebook explains why not.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

FEATURES = ["started_prev_match", "consecutive_starts_before", "start_share_before", "minutes_share_before",
            "minutes_prev_7d", "minutes_prev_14d", "rest_days_filled", "is_gk"]
LEAKAGE_AUDIT = [
    ("started_prev_match", "team's previous match lineup", "known before kick-off"),
    ("consecutive_starts_before", "previous matches", "known before kick-off"),
    ("start_share_before", "starts / team matches before this match", "known before kick-off"),
    ("minutes_share_before", "minutes / (team matches x 95) before this match", "known before kick-off"),
    ("minutes_prev_7d / 14d", "minutes in earlier matches within 7/14 days", "known before kick-off"),
    ("rest_days_filled", "days since last appearance (60 if none)", "known before kick-off"),
    ("is_gk", "role from squad match position (event-derived)", "position played in this match — mild "
                                                                "contemporaneous information; GK role is stable"),
    ("EXCLUDED: minutes_played, events, goals in the match", "same-match outcomes", "would leak — not used"),
]


def build_start_dataset(bundle: Any, team_name: str) -> pd.DataFrame:
    wl = bundle.workload
    app = bundle.tables["appearances"]
    m = bundle.tables["matches"][["match_id", "match_date"]]
    d = app[app["team_name"] == team_name][["match_id", "team_id", "player_id", "player_name", "is_starter",
                                            "match_role"]].merge(wl, on=["match_id", "team_id", "player_id"])
    d = d.merge(m, on="match_id").sort_values(["match_date", "player_id"])
    d = d[d["prior_team_matches"] >= 1].copy()  # first match has no history
    d["started_prev_match"] = d["started_prev_match"].astype(float).fillna(0.0)
    d["rest_days_filled"] = d["rest_days"].fillna(60).clip(upper=60)
    d["is_gk"] = (d["match_role"] == "GK").astype(float)
    d["y"] = d["is_starter"].astype(int)
    return d.reset_index(drop=True)


def fit_start_model(bundle: Any, team_name: str, min_rows: int = 300, min_matches: int = 15,
                    train_frac: float = 0.7) -> dict[str, Any]:
    """Fit logistic regression with a chronological split if the sample gate passes."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import (brier_score_loss, confusion_matrix, f1_score, precision_score, recall_score,
                                 roc_auc_score, roc_curve)
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    d = build_start_dataset(bundle, team_name)
    n_matches = d["match_id"].nunique()
    gate = {"rows": len(d), "matches": n_matches, "min_rows": min_rows, "min_matches": min_matches,
            "class_balance_starter_pct": round(100 * d["y"].mean(), 1) if len(d) else np.nan}
    if len(d) < min_rows or n_matches < min_matches:
        return {"fitted": False, "gate": gate, "reason": "Sample gate not met: descriptive analysis only."}
    order = d[["match_id", "match_date"]].drop_duplicates().sort_values("match_date")
    cut = int(len(order) * train_frac)
    train_ids, test_ids = set(order["match_id"].iloc[:cut]), set(order["match_id"].iloc[cut:])
    tr, te = d[d["match_id"].isin(train_ids)], d[d["match_id"].isin(test_ids)]
    model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, random_state=0))
    model.fit(tr[FEATURES], tr["y"])
    prob = model.predict_proba(te[FEATURES])[:, 1]
    # Decision rule respecting the domain constraint: exactly 11 starters per match.
    te = te.assign(prob=prob)
    te["pred_top11"] = te.groupby("match_id")["prob"].rank(ascending=False, method="first") <= 11
    base = te["started_prev_match"].astype(int)

    def metrics(pred, name, p=None):
        out = {"model": name, "precision": precision_score(te["y"], pred), "recall": recall_score(te["y"], pred),
               "f1": f1_score(te["y"], pred)}
        if p is not None:
            out["roc_auc"] = roc_auc_score(te["y"], p)
            out["brier"] = brier_score_loss(te["y"], p)
        return out

    res = pd.DataFrame([metrics(base, "Baseline: started previous match"),
                        metrics(te["pred_top11"].astype(int), "Logistic regression (top-11 per match)", prob)]).round(3)
    coef = pd.DataFrame({"feature": FEATURES, "coefficient_std": model[-1].coef_[0]}).sort_values(
        "coefficient_std", key=np.abs, ascending=False).round(3)
    fpr, tpr, _ = roc_curve(te["y"], prob)
    bins = pd.cut(te["prob"], [0, .2, .4, .6, .8, 1.0], include_lowest=True)
    calib = te.groupby(bins, observed=True).agg(mean_pred=("prob", "mean"), observed_rate=("y", "mean"),
                                                 n=("y", "size")).reset_index()
    return {"fitted": True, "gate": gate, "train_matches": len(train_ids), "test_matches": len(test_ids),
            "train_rows": len(tr), "test_rows": len(te),
            "split": f"chronological: train up to {order['match_date'].iloc[cut - 1]:%Y-%m-%d}, "
                     f"test from {order['match_date'].iloc[cut]:%Y-%m-%d}",
            "metrics": res, "coefficients": coef,
            "confusion_matrix": confusion_matrix(te["y"], te["pred_top11"].astype(int)),
            "roc": pd.DataFrame({"fpr": fpr, "tpr": tpr}), "calibration": calib, "test_predictions": te,
            "leakage_audit": pd.DataFrame(LEAKAGE_AUDIT, columns=["feature", "computed from", "availability"])}
