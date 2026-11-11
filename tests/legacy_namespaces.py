"""Namespaces that let the unit tests written for the earlier single-package layout address the new modules."""
from __future__ import annotations

from types import SimpleNamespace

from src.analytics import substitution_analysis as _sub_analytics
from src.features import substitution_features as _sub_features


def _merge(*modules) -> SimpleNamespace:
    ns = SimpleNamespace()
    for m in modules:
        for k, v in vars(m).items():
            if not k.startswith("__"):
                setattr(ns, k, v)
    return ns


sa = _merge(_sub_features, _sub_analytics)
