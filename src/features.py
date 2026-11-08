"""features.py — Feature engineering.

Owner: M4

Agreed contract for feature functions. All features use only information up to
and including day t (no leakage).

Feature groups:
  - historical counts: purchase lags 1/2/3/7; views, cart lags 1/7
  - rolling stats: 3/7/14-day means; 7-day std
  - ratios: cart/view, purchase/cart (denominator + small constant)
  - calendar: day-of-week, day-of-month, promotion/holiday flags
  - scale-free: count / trailing-7-day mean, or log1p
  - category identity: one-hot (internal experiments only)
"""

from __future__ import annotations

import pandas as pd


def add_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add lagged counts (t-1, t-2, t-3, t-7 for purchase; t-1, t-7 for views/cart).

    TODO: implement. Use only past data relative to t.
    """
    raise NotImplementedError


def add_rolling_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add rolling means (3/7/14 days) and 7-day std.

    TODO: implement.
    """
    raise NotImplementedError


def add_ratio_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add cart/view and purchase/cart ratios.

    TODO: implement (add a small constant to the denominator).
    """
    raise NotImplementedError


def add_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add day-of-week, day-of-month, and holiday/promotion flags.

    TODO: implement using a public calendar (do not infer from sales).
    """
    raise NotImplementedError


def build_features(
    daily: pd.DataFrame,
    *,
    scale_free: bool = False,
    category_onehot: bool = False,
) -> tuple[pd.DataFrame, list[str]]:
    """Return (feature matrix X, target y) aligned on day t -> t+1.

    TODO: implement and run a leakage audit before use.
    """
    raise NotImplementedError
