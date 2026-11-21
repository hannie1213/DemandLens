"""DemandLens feature layer: M4 window and feature construction."""
from demandlens.features.windows import WINDOW_FIELDS, detect_missing_dates, make_windows
from demandlens.features.build_features import (
    BEHAVIOR_FEATURES,
    CALENDAR_FEATURES,
    PURCHASE_FEATURES,
    build_features,
    feature_columns,
)

__all__ = [
    "make_windows",
    "detect_missing_dates",
    "WINDOW_FIELDS",
    "build_features",
    "feature_columns",
    "PURCHASE_FEATURES",
    "BEHAVIOR_FEATURES",
    "CALENDAR_FEATURES",
]
