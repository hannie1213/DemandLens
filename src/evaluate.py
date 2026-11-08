"""evaluate.py — Metrics, chronological splitting, prediction intervals, importance.

Owner: M6

Agreed evaluation contract. The protocol is frozen in docs/evaluation_protocol.md.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Mean absolute error."""
    raise NotImplementedError


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Root mean squared error."""
    raise NotImplementedError


def wape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Weighted absolute percentage error = sum|err| / sum|actual|."""
    raise NotImplementedError


def improvement_over_baseline(model_mae: float, baseline_mae: float) -> float:
    """1 - model_mae / baseline_mae. Report for B0 and B2."""
    raise NotImplementedError


def rolling_origin_split(daily: pd.DataFrame, *, origin: str, horizon: int = 1):
    """Chronological expanding-window split; all categories of one day together."""
    raise NotImplementedError


def prediction_interval(residuals: np.ndarray, *, alpha: float = 0.9) -> tuple[float, float]:
    """Empirical quantiles of validation residuals (grouped by category size)."""
    raise NotImplementedError


def permutation_importance(model, X: pd.DataFrame, y: np.ndarray, *, n_repeats: int = 5):
    """Permutation importance, shared across all three models."""
    raise NotImplementedError
