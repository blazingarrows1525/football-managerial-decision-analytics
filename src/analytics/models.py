"""Gated start-selection model with a leakage audit and chronological split."""
from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Any

from src.config import ROLE_FAMILY as _ROLE_FAMILY

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


BASELINE_NAME = "Baseline: started previous match"
TARGET_DEFINITION = ("y = 1 when the squad member started the match, 0 when he was named on the bench. One row per "
                     "match-day squad member of the focus team; the team's first analysed match is dropped because "
                     "it has no history.")
UNSUPPORTED_TARGETS = [
    ("Match result (win / draw / loss)", "34 matches of one team with no losses; the classes cannot be separated "
                                         "and nothing would generalise beyond this team-season."),
    ("Goals or xG per match (regression)", "34 observations for a model with several predictors: any fit would "
                                           "be noise."),
    ("Injury risk, fitness or fatigue", "No injury, medical, GPS or physical-load data exist in the source."),
    ("Player market value", "No valuation or contract data exist in the source."),
]


def _model_factories(seed: int) -> dict[str, Any]:
    from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    return {
        "Logistic regression": lambda: make_pipeline(StandardScaler(),
                                                     LogisticRegression(max_iter=1000, random_state=seed)),
        "Random forest": lambda: RandomForestClassifier(400, min_samples_leaf=5, random_state=seed, n_jobs=-1),
        "Gradient boosting": lambda: GradientBoostingClassifier(random_state=seed),
    }


def top11(frame: pd.DataFrame, prob: Any) -> pd.Series:
    """Decision rule that respects the domain constraint: the eleven highest probabilities per match start."""
    return (frame.assign(p=prob).groupby("match_id")["p"].rank(ascending=False, method="first") <= 11).astype(int)


def compare_start_models(bundle: Any, team_name: str, seed: int = 42, n_splits: int = 5, train_frac: float = 0.7,
                         min_rows: int = 300, min_matches: int = 15) -> dict[str, Any]:
    """Baseline and three classifiers under expanding-window cross-validation and a chronological hold-out.

    Folds are split by *match* (train matches always precede test matches) so no squad member of a test match
    is seen in training for that match and no future information reaches the features.
    """
    from sklearn.metrics import (accuracy_score, average_precision_score, brier_score_loss, confusion_matrix,
                                 f1_score, precision_recall_curve, precision_score, recall_score, roc_auc_score,
                                 roc_curve)
    from sklearn.model_selection import TimeSeriesSplit

    ds = build_start_dataset(bundle, team_name)
    n_matches = ds["match_id"].nunique() if len(ds) else 0
    gate = {"rows": len(ds), "matches": n_matches, "min_rows": min_rows, "min_matches": min_matches,
            "class_balance_starter_pct": round(100 * ds["y"].mean(), 1) if len(ds) else np.nan}
    if len(ds) < min_rows or n_matches < min_matches:
        return {"fitted": False, "gate": gate,
                "reason": "Sample gate not met: the result would not be statistically supportable."}
    mt = ds[["match_id", "match_date"]].drop_duplicates().sort_values("match_date").reset_index(drop=True)
    ds = ds.assign(m_idx=ds["match_id"].map(dict(zip(mt["match_id"], mt.index))))
    factories = _model_factories(seed)

    cv_rows = []
    for fold, (tr_m, te_m) in enumerate(TimeSeriesSplit(n_splits=n_splits).split(mt)):
        tr, te = ds[ds["m_idx"].isin(tr_m)], ds[ds["m_idx"].isin(te_m)]
        base = te["started_prev_match"].astype(int)
        cv_rows.append({"model": BASELINE_NAME, "fold": fold, "train_matches": len(tr_m), "test_matches": len(te_m),
                        "accuracy": accuracy_score(te["y"], base), "precision": precision_score(te["y"], base),
                        "recall": recall_score(te["y"], base), "f1": f1_score(te["y"], base)})
        for name, make in factories.items():
            m = make().fit(tr[FEATURES], tr["y"])
            pr = m.predict_proba(te[FEATURES])[:, 1]
            pred = top11(te, pr)
            cv_rows.append({"model": name, "fold": fold, "train_matches": len(tr_m), "test_matches": len(te_m),
                            "accuracy": accuracy_score(te["y"], pred), "precision": precision_score(te["y"], pred),
                            "recall": recall_score(te["y"], pred), "f1": f1_score(te["y"], pred),
                            "roc_auc": roc_auc_score(te["y"], pr), "pr_auc": average_precision_score(te["y"], pr),
                            "brier": brier_score_loss(te["y"], pr)})
    cv = pd.DataFrame(cv_rows)
    metric_cols = ["accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc", "brier"]
    cv_summary = cv.groupby("model")[metric_cols].agg(["mean", "std"])

    cut = int(len(mt) * train_frac)
    tr, te = ds[ds["m_idx"] < cut], ds[ds["m_idx"] >= cut]
    fitted = {n: make().fit(tr[FEATURES], tr["y"]) for n, make in factories.items()}
    probs = {n: m.predict_proba(te[FEATURES])[:, 1] for n, m in fitted.items()}
    base = te["started_prev_match"].astype(int)
    curves, hold_rows = {}, [{"model": BASELINE_NAME, "precision": precision_score(te["y"], base),
                              "recall": recall_score(te["y"], base), "f1": f1_score(te["y"], base),
                              "brier": brier_score_loss(te["y"], base.astype(float))}]
    for n, p in probs.items():
        fpr, tpr, _ = roc_curve(te["y"], p)
        prec, rec, _ = precision_recall_curve(te["y"], p)
        curves[n] = {"fpr": fpr, "tpr": tpr, "precision": prec, "recall": rec}
        pred = top11(te, p)
        hold_rows.append({"model": n, "precision": precision_score(te["y"], pred),
                          "recall": recall_score(te["y"], pred), "f1": f1_score(te["y"], pred),
                          "roc_auc": roc_auc_score(te["y"], p), "pr_auc": average_precision_score(te["y"], p),
                          "brier": brier_score_loss(te["y"], p)})
    holdout = pd.DataFrame(hold_rows)
    best = max(probs, key=lambda n: roc_auc_score(te["y"], probs[n]))
    te_best = te.assign(prob=probs[best], pred=top11(te, probs[best]).to_numpy())
    te_best["residual"] = te_best["y"] - te_best["prob"]

    thr_rows = []
    for t in np.round(np.arange(0.1, 0.91, 0.05), 2):
        pred = (te_best["prob"] >= t).astype(int)
        thr_rows.append({"threshold": t, "precision": precision_score(te_best["y"], pred, zero_division=0),
                         "recall": recall_score(te_best["y"], pred, zero_division=0),
                         "f1": f1_score(te_best["y"], pred, zero_division=0),
                         "predicted_starters_per_match": pred.groupby(te_best["match_id"]).sum().mean()})
    bins = pd.cut(te_best["prob"], [0, .2, .4, .6, .8, 1.0], include_lowest=True)
    calibration = te_best.groupby(bins, observed=True).agg(mean_pred=("prob", "mean"), observed_rate=("y", "mean"),
                                                            n=("y", "size")).reset_index()

    # learning curve: train on the first k matches, always test on the same chronological hold-out
    lc_rows = []
    for k in range(5, cut + 1, max(1, (cut - 5) // 6 or 1)):
        sub = ds[ds["m_idx"] < k]
        if sub["y"].nunique() < 2:
            continue
        m = factories[best]().fit(sub[FEATURES], sub["y"])
        lc_rows.append({"train_matches": k, "train_rows": len(sub),
                        "holdout_auc": roc_auc_score(te["y"], m.predict_proba(te[FEATURES])[:, 1]),
                        "train_auc": roc_auc_score(sub["y"], m.predict_proba(sub[FEATURES])[:, 1])})

    te_best["role_family"] = te_best["match_role"].map(_ROLE_FAMILY).fillna("Bench role not recorded")
    subgroup = te_best.groupby("role_family").agg(n=("y", "size"), starters=("y", "sum"),
                                                  error_rate=("pred", lambda s: float(
                                                      (s != te_best.loc[s.index, "y"]).mean())),
                                                  mean_abs_residual=("residual", lambda s: float(s.abs().mean()))
                                                  ).reset_index()
    return {"fitted": True, "gate": gate, "dataset": ds, "cv": cv, "cv_summary": cv_summary, "holdout": holdout,
            "curves": curves, "best": best, "models": fitted, "probs": probs, "test": te, "train": tr,
            "test_best": te_best, "confusion_matrix": confusion_matrix(te["y"], te_best["pred"]),
            "thresholds": pd.DataFrame(thr_rows), "calibration": calibration,
            "learning_curve": pd.DataFrame(lc_rows), "subgroup": subgroup, "features": list(FEATURES),
            "baseline_point": {"fpr": 1 - recall_score(1 - te["y"], 1 - base), "tpr": recall_score(te["y"], base),
                               "precision": precision_score(te["y"], base), "recall": recall_score(te["y"], base)},
            "split": {"train_matches": cut, "test_matches": len(mt) - cut,
                      "train_until": mt["match_date"].iloc[cut - 1], "test_from": mt["match_date"].iloc[cut],
                      "train_rows": len(tr), "test_rows": len(te),
                      "test_positive_rate": float(te["y"].mean())},
            "target": TARGET_DEFINITION, "positive_class": "started the match (y = 1)",
            "leakage_audit": pd.DataFrame(LEAKAGE_AUDIT, columns=["feature", "computed from", "availability"])}
