"""models.py — Baselines and regression models, plus a shared predict() interface.

Owner: M5

The app loads a trained model and calls predict(); it never trains at runtime.

Baselines:
  B0 persistence (tomorrow = today)
  B1 same weekday last week
  B2 7-day moving average

Models:
  KNN regression, Decision Tree regression, Random Forest regression.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def baseline_persistence(history: pd.Series) -> float:
    """B0: forecast = last observed purchase count.

    TODO: implement.
    """
    raise NotImplementedError


def baseline_same_weekday(history: pd.Series) -> float:
    """B1: forecast = same weekday of the previous week.

    TODO: implement.
    """
    raise NotImplementedError


def baseline_moving_average(history: pd.Series, window: int = 7) -> float:
    """B2: forecast = mean of the last `window` days.

    TODO: implement.
    """
    raise NotImplementedError


def fit_knn(X: pd.DataFrame, y: pd.Series, **params):
    """Fit KNN regression. Features must be standardized first.

    TODO: implement.
    """
    raise NotImplementedError


def fit_decision_tree(X: pd.DataFrame, y: pd.Series, **params):
    """Fit Decision Tree regression. Output is bounded by training values.

    TODO: implement.
    """
    raise NotImplementedError


def fit_random_forest(X: pd.DataFrame, y: pd.Series, **params):
    """Fit Random Forest regression. Limit trees/depth to keep the file small.

    TODO: implement.
    """
    raise NotImplementedError


def predict(model, X: pd.DataFrame) -> np.ndarray:
    """Shared predict() interface used by the app and evaluation.

    TODO: implement.
    """
    raise NotImplementedError


def save_model(model, path: str) -> None:
    """Persist a fitted model to joblib.

    TODO: implement.
    """
    raise NotImplementedError


def load_model(path: str):
    """Load a joblib model.

    TODO: implement.
    """
    raise NotImplementedError
