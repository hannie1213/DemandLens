"""M4 feature engineering: turn per-category windows into a feature table.

One shared implementation for training, experiments and website inference
(train/serve parity). Every feature is computed from the input window only
(prediction origin and earlier); the target period is never read, so this
function is safe to call on website rows that have no ``y``.

``config`` is a dict with these keys (see ``scripts/build_features.py`` for how
it is assembled from ``config/config.yaml`` plus the daily table):

- ``daily_rows`` (required): list of daily dicts with the ``daily_category.csv``
  contract keys ``date``, ``category_id``, ``views``, ``cart``, ``purchase``.
- ``category_ids`` (optional): list of category-id strings used for the
  one-hot columns. Pass the M3 development-period selection (config
  ``variants['10'].selected_ids``) so the encoding is fit on development data
  only and never sees the test period. If omitted, the unique ids in ``windows``
  are used as a fallback.
- ``holidays`` (optional): iterable of ISO date strings (public holidays). The
  holiday flag is set when any target-week day is in this list. Default empty.
"""
from collections import defaultdict
from datetime import timedelta

from ..data.quality import day_range, parse_day

# Always-on purchase features.
PURCHASE_FEATURES = [
    "purchase_last7_total",
    "purchase_prev7_total",
    "purchase_last14_total",
    "purchase_last7_avg",
    "purchase_trend",
]

# Behavior (views/cart) totals + trends, plus event-count ratios. use_behavior.
BEHAVIOR_FEATURES = [
    "views_last7_total",
    "views_prev7_total",
    "views_trend",
    "cart_last7_total",
    "cart_prev7_total",
    "cart_trend",
    "cart_view_ratio",
    "purchase_cart_ratio",
    "purchase_wow_ratio",
]

# Calendar features describing the target week (deterministic, known ahead).
CALENDAR_FEATURES = [
    "cal_target_weekday",
    "cal_target_month",
    "cal_target_cross_month",
    "cal_target_holiday",
]

# Window fields carried into the feature table (y is re-appended at the end).
WINDOW_META_FIELDS = [
    "sample_id",
    "category_id",
    "input_start_date",
    "input_end_date",
    "target_start_date",
    "target_end_date",
]


def feature_columns(config, use_behavior=True, use_category=True):
    """Ordered feature column names for the given switches and config."""
    cols = list(PURCHASE_FEATURES)
    if use_behavior:
        cols += BEHAVIOR_FEATURES
    cols += CALENDAR_FEATURES
    if use_category:
        for cid in sorted((str(c) for c in config.get("category_ids", [])), key=int):
            cols.append(f"cat_is_{cid}")
    return cols


def _trend(last, prev):
    """Week-over-week relative change; neutral ``0.0`` when ``prev`` is 0."""
    if prev == 0:
        return 0.0
    return (last - prev) / prev


def _wow_ratio(last, prev):
    """Week-over-week ratio; neutral ``1.0`` when ``prev`` is 0."""
    if prev == 0:
        return 1.0
    return last / prev


def _conv_ratio(numerator, denominator):
    """Event-count conversion ratio; neutral ``0.0`` when denominator is 0."""
    if denominator == 0:
        return 0.0
    return numerator / denominator


def build_features(windows, config, use_behavior=True, use_category=True):
    """Build the feature table for a list of windows.

    Parameters
    ----------
    windows : iterable of dict
        Window records from ``make_windows`` (keys ``sample_id``,
        ``category_id``, ``input_start_date``, ``input_end_date``,
        ``target_start_date``, ``target_end_date`` and optionally ``y``).
    config : dict
        See module docstring for ``daily_rows``, ``category_ids``, ``holidays``.
    use_behavior : bool
        ``True`` adds views/cart totals + trends and the ratio features (E2).
        ``False`` keeps only purchase and calendar features.
    use_category : bool
        ``True`` adds one-hot ``cat_is_<id>`` columns for each configured
        category (E3). The mapping is taken from ``config['category_ids']``,
        i.e. the development-period selection, never the test period.

    Returns
    -------
    list of dict
        One row per window: the window metadata fields, the feature columns,
        and ``y`` when present in the input window.
    """
    daily_rows = config["daily_rows"]
    holidays = set(config.get("holidays", []))
    category_ids = [str(c) for c in config.get("category_ids", [])]

    # category_id -> {ISO date: (views, cart, purchase)}
    by_category = defaultdict(dict)
    for row in daily_rows:
        cid = str(row["category_id"])
        by_category[cid][row["date"]] = (
            int(row["views"]),
            int(row["cart"]),
            int(row["purchase"]),
        )

    one_hot_ids = sorted(category_ids, key=int) if use_category else []

    table = []
    for w in windows:
        cid = str(w["category_id"])
        input_start = parse_day(w["input_start_date"])
        input_end = parse_day(w["input_end_date"])
        target_start = parse_day(w["target_start_date"])
        target_end = parse_day(w["target_end_date"])
        events = by_category.get(cid, {})

        def window_sum(event_idx, start, end):
            """Sum one event column over [start, end], clipped to the input
            window so no target or pre-input day is ever read."""
            start = max(start, input_start)
            end = min(end, input_end)
            if start > end:
                return 0
            return sum(
                events.get(d, (0, 0, 0))[event_idx]
                for d in day_range(start.isoformat(), end.isoformat())
            )

        last7_start = input_end - timedelta(days=6)
        prev7_start = input_end - timedelta(days=13)
        prev7_end = input_end - timedelta(days=7)

        p_last7 = window_sum(2, last7_start, input_end)
        p_prev7 = window_sum(2, prev7_start, prev7_end)
        p_last14 = window_sum(2, prev7_start, input_end)
        n_last7 = (input_end - max(last7_start, input_start)).days + 1
        p_avg = p_last7 / n_last7 if n_last7 else 0.0

        feats = {
            "purchase_last7_total": p_last7,
            "purchase_prev7_total": p_prev7,
            "purchase_last14_total": p_last14,
            "purchase_last7_avg": p_avg,
            "purchase_trend": _trend(p_last7, p_prev7),
        }

        if use_behavior:
            v_last7 = window_sum(0, last7_start, input_end)
            v_prev7 = window_sum(0, prev7_start, prev7_end)
            c_last7 = window_sum(1, last7_start, input_end)
            c_prev7 = window_sum(1, prev7_start, prev7_end)
            feats.update({
                "views_last7_total": v_last7,
                "views_prev7_total": v_prev7,
                "views_trend": _trend(v_last7, v_prev7),
                "cart_last7_total": c_last7,
                "cart_prev7_total": c_prev7,
                "cart_trend": _trend(c_last7, c_prev7),
                "cart_view_ratio": _conv_ratio(c_last7, v_last7),
                "purchase_cart_ratio": _conv_ratio(p_last7, c_last7),
                "purchase_wow_ratio": _wow_ratio(p_last7, p_prev7),
            })

        # Calendar features describe the target week, which is deterministic and
        # known ahead of the forecast origin (no event data is read).
        feats.update({
            "cal_target_weekday": target_start.weekday(),
            "cal_target_month": target_start.month,
            "cal_target_cross_month": 1 if target_start.month != target_end.month else 0,
            "cal_target_holiday": int(any(
                d in holidays
                for d in day_range(target_start.isoformat(), target_end.isoformat())
            )),
        })

        if use_category:
            for oid in one_hot_ids:
                feats[f"cat_is_{oid}"] = 1 if cid == oid else 0

        row = {k: w[k] for k in WINDOW_META_FIELDS}
        row.update(feats)
        if "y" in w:
            row["y"] = w["y"]
        table.append(row)

    return table
