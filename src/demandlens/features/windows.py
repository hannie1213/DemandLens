"""M4 window construction: per-category sliding input/target windows.

The returned window records use the same key names that
``demandlens.evaluation.splits.split_by_time`` reads (``input_start_date``,
``input_end_date``, ``target_start_date``, ``target_end_date``,
``category_id``), so they can be handed to the M3 splitter and to the M4
feature builder without reshaping.
"""
from collections import defaultdict
from datetime import timedelta

from ..data.quality import day_range, parse_day

# Column contract shared by the in-memory window records and the exported CSVs.
WINDOW_FIELDS = [
    "sample_id",
    "category_id",
    "input_start_date",
    "input_end_date",
    "target_start_date",
    "target_end_date",
    "y",
]


def detect_missing_dates(rows):
    """Return ``{category_id: {missing ISO dates}}`` within each category's span.

    A calendar day missing between a category's first and last observed day is
    treated as an unresolved collection gap, never as a silent zero. The
    primary store is calendar-complete, so this is normally empty, but the
    check is kept explicit so a gap cannot be averaged away.
    """
    present = defaultdict(set)
    for row in rows:
        present[str(row["category_id"])].add(row["date"])
    gaps = {}
    for category_id, dates in present.items():
        missing = set(day_range(min(dates), max(dates))) - dates
        if missing:
            gaps[category_id] = missing
    return gaps


def make_windows(daily_df, lookback, horizon, step):
    """Build per-category sliding windows from a daily category table.

    Parameters
    ----------
    daily_df : iterable of dict
        Daily rows with the ``daily_category.csv`` contract keys ``date``,
        ``category_id``, ``views``, ``cart`` and ``purchase``.
    lookback : int
        Input-window length in days (the history available to features).
    horizon : int
        Target-window length in days (the forecast span used to compute ``y``).
    step : int
        Number of days between consecutive prediction origins.

    Returns
    -------
    (windows, meta)
        ``windows`` is a list of records with keys ``sample_id``,
        ``category_id``, ``input_start_date``, ``input_end_date``,
        ``target_start_date``, ``target_end_date`` and ``y``. ``y`` is the
        scalar sum of ``purchase`` events over the target days only.
        ``meta`` records the windowing parameters and the global input/target
        date span.

    Leakage contract (enforced by construction, re-checked by the tests):
        input_start <= input_end < target_start <= target_end,
        target_start == input_end + 1 day,
        input length == lookback and target length == horizon,
        any window whose input or target touches a collection gap is excluded
        (never zero-filled).
    """
    if type(lookback) != int or type(horizon) != int or type(step) != int:
        raise ValueError("lookback, horizon and step must be integers")
    if min(lookback, horizon, step) < 1:
        raise ValueError("lookback, horizon and step must be >= 1")

    rows = list(daily_df)
    gaps = detect_missing_dates(rows)

    # category_id -> {ISO date: purchase count}
    by_category = defaultdict(dict)
    for row in rows:
        by_category[str(row["category_id"])][row["date"]] = int(row["purchase"])

    windows = []
    for category_id in sorted(by_category, key=int):
        dates = sorted(by_category[category_id])
        first = parse_day(dates[0])
        last = parse_day(dates[-1])
        gap_set = gaps.get(category_id, set())

        origin = first + timedelta(days=lookback - 1)
        last_origin = last - timedelta(days=horizon)
        while origin <= last_origin:
            input_start = origin - timedelta(days=lookback - 1)
            target_start = origin + timedelta(days=1)
            target_end = origin + timedelta(days=horizon)

            # Drop any window whose span overlaps an unresolved collection gap.
            span = set(day_range(input_start.isoformat(), target_end.isoformat()))
            if span & gap_set:
                origin += timedelta(days=step)
                continue

            y = sum(
                by_category[category_id][day]
                for day in day_range(target_start.isoformat(), target_end.isoformat())
            )
            windows.append({
                "sample_id": len(windows),
                "category_id": category_id,
                "input_start_date": input_start.isoformat(),
                "input_end_date": origin.isoformat(),
                "target_start_date": target_start.isoformat(),
                "target_end_date": target_end.isoformat(),
                "y": y,
            })
            origin += timedelta(days=step)

    if not windows:
        raise ValueError(
            "No windows fit the given lookback/horizon/step for this daily table"
        )

    meta = {
        "lookback": lookback,
        "horizon": horizon,
        "step": step,
        "n_windows": len(windows),
        "n_categories": len(by_category),
        "input_start": min(w["input_start_date"] for w in windows),
        "input_end": max(w["input_end_date"] for w in windows),
        "target_start": min(w["target_start_date"] for w in windows),
        "target_end": max(w["target_end_date"] for w in windows),
    }
    return windows, meta
