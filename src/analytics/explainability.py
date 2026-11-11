"""Model explanation for the start-selection models: permutation importance, partial dependence, SHAP.

Explanations describe how a fitted model uses its features. They are conditional on the other features and
are not causal levers; they are only produced after the model has passed its sample gate.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def permutation_table(result: dict[str, Any], model_name: str | None = None, n_repeats: int = 30, seed: int = 42
                      ) -> pd.DataFrame:
    """Mean drop in hold-out ROC-AUC when each feature is shuffled (with the spread over repeats)."""
    from sklearn.inspection import permutation_importance

    name = model_name or result["best"]
    te, feats = result["test"], result["features"]
    pim = permutation_importance(result["models"][name], te[feats], te["y"], scoring="roc_auc",
                                 n_repeats=n_repeats, random_state=seed)
    out = pd.DataFrame({"feature": feats, "importance_mean": pim.importances_mean,
                        "importance_std": pim.importances_std})
    out["model"] = name
    return out.sort_values("importance_mean").reset_index(drop=True)


def partial_dependence_table(result: dict[str, Any], feature: str, model_name: str | None = None,
                             grid_resolution: int = 25, ice_sample: int = 60, seed: int = 42) -> dict[str, Any]:
    """Average (PDP) and per-row (ICE) predicted start probability across the range of one feature."""
    from sklearn.inspection import partial_dependence

    name = model_name or result["best"]
    te, feats = result["test"], result["features"]
    pd_res = partial_dependence(result["models"][name], te[feats], [feature], kind="both",
                                grid_resolution=grid_resolution)
    grid = np.asarray(pd_res["grid_values"][0] if "grid_values" in pd_res else pd_res["values"][0], float)
    ice = np.asarray(pd_res["individual"][0], float)
    rng = np.random.default_rng(seed)
    keep = rng.choice(len(ice), min(ice_sample, len(ice)), replace=False)
    return {"feature": feature, "model": name, "grid": grid, "average": np.asarray(pd_res["average"][0], float),
            "ice": ice[keep], "n_rows": len(ice)}


def shap_values_table(result: dict[str, Any]) -> dict[str, Any]:
    """SHAP values of the gradient-boosting model on the hold-out. Returns a status when SHAP is unavailable."""
    try:
        import shap
    except Exception as exc:  # optional dependency
        return {"status": f"SHAP is not installed ({type(exc).__name__}); permutation importance and partial "
                          f"dependence remain available."}
    te, feats = result["test"], result["features"]
    model = result["models"].get("Gradient boosting")
    if model is None:
        return {"status": "No tree model was fitted."}
    try:
        values = np.asarray(shap.TreeExplainer(model).shap_values(te[feats]), float)
    except Exception as exc:
        return {"status": f"SHAP could not explain this model ({type(exc).__name__})."}
    rank = pd.Series(np.abs(values).mean(axis=0), index=feats).sort_values(ascending=False)
    return {"status": "ok", "values": values, "features": feats, "data": te[feats].reset_index(drop=True),
            "mean_abs": rank, "model": "Gradient boosting"}
