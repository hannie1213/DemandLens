"""Aggregate counts by "date x category" and produce check statistics (requirement D2, contract 3.6).

Rules (consistent with assignment 3.6/3.7):
- Only aggregate the three event types view / cart / purchase; other event types (e.g.
  remove_from_cart) are counted separately and written to the check table, not the daily aggregate.
- The date is the UTC date of event_time (raw string shaped like ``2019-10-01 00:00:05 UTC``,
  fixed format; take the first 10 chars then parse with a strict format and count invalid values).
- No zero-fill and no category filtering (missing (category, date) combos are left for M3 to review and fill).
- Totals per event type must be identical before vs after aggregation (D2 acceptance), written by
  build_aggregation_check to aggregation_check.csv.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from demandlens.data.loader import CONTRACT_EVENTS, iter_event_chunks

DAILY_COLUMNS = ["date", "category_id", "category_code", "views", "cart", "purchase"]

_MONTH_NUM = {
    "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04", "May": "05", "Jun": "06",
    "Jul": "07", "Aug": "08", "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12",
}


def month_label_from_filename(path: str | Path) -> str:
    """``2019-Oct.csv`` -> ``2019-10``."""
    stem = Path(path).stem
    year, mon = stem.split("-")
    return f"{year}-{_MONTH_NUM[mon]}"


def _empty_stats() -> Dict:
    return {
        "file": "",
        "month_label": "",
        "raw_rows": 0,
        "aggregatable_rows": 0,
        "event_counts": Counter(),
        "contract_kept": Counter(),
        "invalid_date_rows": 0,
        "invalid_category_rows": 0,
        "duplicate_within_chunks": 0,
        "missing_category_code_events": 0,
        "category_codes": {},
    }


def aggregate_chunk(chunk: pd.DataFrame, stats: Dict) -> pd.DataFrame:
    """Process one chunk: update check statistics, return that chunk's (date, category) x event-count partial table."""
    event_type = chunk["event_type"].str.strip().str.lower().fillna("<MISSING>")
    stats["raw_rows"] += len(chunk)
    stats["event_counts"].update(event_type.value_counts().to_dict())

    # Estimate of rows identical on the four contract columns. Reading does not include user_id,
    # so multiple normal same-second events of a popular product also count -- this is a
    # "suspected duplicate" signal, not a true duplicate, provided for M3's reference.
    stats["duplicate_within_chunks"] += int(chunk.duplicated().sum())

    # Date: fixed prefix format, strict parse; count invalid rows and exclude them from aggregation
    date_str = chunk["event_time"].str.slice(0, 10)
    valid_date = pd.to_datetime(date_str, format="%Y-%m-%d", errors="coerce").notna()

    # Category: category_id must parse as integer; count invalid rows and exclude them from aggregation
    category_id = pd.to_numeric(chunk["category_id"], errors="coerce")

    # Excluded rows = invalid date OR invalid category (regardless of event type; these rows do not enter the daily aggregate)
    excluded = (~valid_date) | category_id.isna()
    stats["invalid_date_rows"] += int((~valid_date).sum())
    stats["invalid_category_rows"] += int((category_id.isna() & valid_date).sum())

    keep = (~excluded) & event_type.isin(CONTRACT_EVENTS)
    stats["aggregatable_rows"] += int(keep.sum())
    stats["contract_kept"].update(event_type[keep].value_counts().to_dict())

    if keep.any():
        kept = chunk.loc[keep]
        stats["missing_category_code_events"] += int(kept["category_code"].isna().sum())
        codes = (
            kept.loc[kept["category_code"].notna()]
            .groupby("category_id")["category_code"]
            .agg(lambda s: set(s.unique()))
        )
        for cat, code_set in codes.items():
            stats["category_codes"].setdefault(cat, set()).update(code_set)

        work = pd.DataFrame(
            {
                "date": date_str[keep],
                "category_id": category_id[keep].astype("int64"),
                "event_type": event_type[keep],
            }
        )
        partial = (
            work.groupby(["date", "category_id", "event_type"]).size().unstack("event_type")
            .reindex(columns=list(CONTRACT_EVENTS), fill_value=0)
            .reset_index()
            .rename(columns={"view": "views"})
        )
        return partial
    return pd.DataFrame(
        {"date": pd.Series(dtype="string"), "category_id": pd.Series(dtype="int64"),
         "views": pd.Series(dtype="int64"), "cart": pd.Series(dtype="int64"),
         "purchase": pd.Series(dtype="int64")}
    )


def _canonical_code(code_set: set) -> Optional[str]:
    if not code_set:
        return None
    if len(code_set) == 1:
        return next(iter(code_set))
    return "|".join(sorted(code_set))


def aggregate_month(
    path: str | Path,
    chunksize: int = 1_000_000,
    progress_every: int | None = None,
) -> tuple[pd.DataFrame, Dict]:
    """Aggregate a single month file, returning (daily partial table, check statistics)."""
    stats = _empty_stats()
    stats["file"] = str(path)
    stats["month_label"] = month_label_from_filename(path)
    partials: List[pd.DataFrame] = []
    n_chunks = 0
    for chunk in iter_event_chunks(path, chunksize=chunksize):
        partials.append(aggregate_chunk(chunk, stats))
        n_chunks += 1
        if progress_every and n_chunks % progress_every == 0:
            print(f"    {Path(path).name}: processed {n_chunks} chunks / {stats['raw_rows']:,} rows",
                  flush=True)

    partials = [p for p in partials if len(p)]
    if partials:
        daily = (
            pd.concat(partials, ignore_index=True)
            .groupby(["date", "category_id"], as_index=False)[["views", "cart", "purchase"]]
            .sum()
        )
    else:
        daily = pd.DataFrame(columns=["date", "category_id", "views", "cart", "purchase"])

    daily["category_code"] = (
        daily["category_id"]
        .astype(str)
        .map(lambda c: _canonical_code(stats["category_codes"].get(c, set())))
    )
    daily[["views", "cart", "purchase"]] = daily[
        ["views", "cart", "purchase"]
    ].astype("int64")
    daily = daily[DAILY_COLUMNS].sort_values(["date", "category_id"], ignore_index=True)

    stats["file_bytes"] = Path(path).stat().st_size
    stats["n_chunks"] = n_chunks
    stats["categories_covered"] = int(daily["category_id"].nunique())
    stats["dates_covered"] = int(daily["date"].nunique())
    stats["category_code_conflicts"] = sum(
        1 for s in stats["category_codes"].values() if len(s) > 1
    )
    return daily, stats


def combine_monthly(monthly: List[pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Merge daily aggregates across months; returns (merged table, cross-month category-code consistency table).

    The same (date, category) in principle appears in only one month file; we still sum as a fallback.
    When category_code is inconsistent across months, take the lexicographically smallest and mark it in the consistency table.
    """
    if not monthly:
        raise ValueError("no months to merge")
    stacked = pd.concat(monthly, ignore_index=True)
    consistency = (
        stacked.groupby("category_id")["category_code"]
        .agg(lambda s: set(s.dropna().unique()))
        .reset_index(name="codes_seen")
    )
    consistency["consistent"] = consistency["codes_seen"].map(lambda s: len(s) <= 1)
    code_by_cat = {
        cat: _canonical_code(s)
        for cat, s in zip(consistency["category_id"], consistency["codes_seen"])
    }
    combined = (
        stacked.groupby(["date", "category_id"], as_index=False)
        .agg(views=("views", "sum"), cart=("cart", "sum"), purchase=("purchase", "sum"))
    )
    combined["category_code"] = combined["category_id"].map(code_by_cat)
    combined[["views", "cart", "purchase"]] = combined[
        ["views", "cart", "purchase"]
    ].astype("int64")
    combined = combined[DAILY_COLUMNS].sort_values(["date", "category_id"], ignore_index=True)
    return combined, consistency


def build_aggregation_check(
    dataset: str,
    month_stats: List[Dict],
    monthly_dailies: List[pd.DataFrame],
    consistency: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """Write each month's check statistics into aggregation_check.csv (D2 acceptance: totals identical before vs after aggregation).

    Core invariant (one row per check item):
    - count:{event}     raw event count == that month's daily aggregate column sum  -> OK/FAIL
    - aggregatable_rows rows entering aggregation == sum of the three daily aggregate columns -> OK/FAIL
    - the rest are informational (INFO): excluded rows, within-chunk duplicate estimate, coverage, code conflicts, etc.
    """
    rows: List[Dict] = []
    by_label = {st["month_label"]: (st, daily) for st, daily in zip(month_stats, monthly_dailies)}

    for label, (st, daily) in sorted(by_label.items()):
        month = Path(st["file"]).stem
        for event, col in (("view", "views"), ("cart", "cart"), ("purchase", "purchase")):
            raw_kept = int(st["contract_kept"].get(event, 0))
            agg = int(daily[col].sum()) if len(daily) else 0
            rows.append(dict(dataset=dataset, month=month, check=f"count:{event}",
                             raw_value=raw_kept, aggregated_value=agg,
                             diff=agg - raw_kept, status="OK" if agg == raw_kept else "FAIL"))
            raw_all = int(st["event_counts"].get(event, 0))
            rows.append(dict(dataset=dataset, month=month, check=f"count_raw_all:{event}",
                             raw_value=raw_all, aggregated_value=None, diff=None,
                             status="INFO"))
        agg_rows = int(daily[["views", "cart", "purchase"]].sum().sum()) if len(daily) else 0
        rows.append(dict(dataset=dataset, month=month, check="aggregatable_rows",
                         raw_value=int(st["aggregatable_rows"]), aggregated_value=agg_rows,
                         diff=agg_rows - int(st["aggregatable_rows"]),
                         status="OK" if agg_rows == int(st["aggregatable_rows"]) else "FAIL"))
        other_events = sum(
            n for ev, n in st["event_counts"].items() if ev not in CONTRACT_EVENTS
        )
        rows.append(dict(dataset=dataset, month=month, check="excluded:other_event_types",
                         raw_value=int(other_events), aggregated_value=None, diff=None,
                         status="INFO"))
        # Row conservation: raw = aggregatable + invalid date + invalid category + event type out of contract (with valid date and category)
        residual = (st["raw_rows"] - st["aggregatable_rows"] - st["invalid_date_rows"]
                    - st["invalid_category_rows"])
        rows.append(dict(dataset=dataset, month=month, check="excluded:valid_but_other_event",
                         raw_value=int(residual), aggregated_value=None, diff=None,
                         status="INFO"))
        rows.append(dict(dataset=dataset, month=month, check="invalid:date_rows",
                         raw_value=int(st["invalid_date_rows"]), aggregated_value=None,
                         diff=None, status="INFO"))
        rows.append(dict(dataset=dataset, month=month, check="invalid:category_rows",
                         raw_value=int(st["invalid_category_rows"]), aggregated_value=None,
                         diff=None, status="INFO"))
        rows.append(dict(dataset=dataset, month=month, check="duplicate:same_contract_cols_est",
                         raw_value=int(st["duplicate_within_chunks"]), aggregated_value=None,
                         diff=None, status="INFO"))
        rows.append(dict(dataset=dataset, month=month, check="missing:category_code_in_events",
                         raw_value=int(st["missing_category_code_events"]), aggregated_value=None,
                         diff=None, status="INFO"))
        rows.append(dict(dataset=dataset, month=month, check="consistency:category_code_conflicts",
                         raw_value=int(st["category_code_conflicts"]), aggregated_value=None,
                         diff=None, status="INFO"))
        rows.append(dict(dataset=dataset, month=month, check="coverage:categories",
                         raw_value=int(st["categories_covered"]), aggregated_value=None,
                         diff=None, status="INFO"))
        rows.append(dict(dataset=dataset, month=month, check="coverage:dates",
                         raw_value=int(st["dates_covered"]), aggregated_value=None,
                         diff=None, status="INFO"))
        rows.append(dict(dataset=dataset, month=month, check="file:size_bytes",
                         raw_value=int(st["file_bytes"]), aggregated_value=None,
                         diff=None, status="INFO"))

    if consistency is not None and len(consistency):
        rows.append(dict(dataset=dataset, month="ALL",
                         check="cross_month:category_code_conflicts",
                         raw_value=int((~consistency["consistent"]).sum()),
                         aggregated_value=None, diff=None, status="INFO"))
        rows.append(dict(dataset=dataset, month="ALL", check="combined:rows",
                         raw_value=len(pd.concat(monthly_dailies, ignore_index=True)),
                         aggregated_value=len(consistency) and len(
                             pd.concat(monthly_dailies, ignore_index=True)
                             .groupby(["date", "category_id"])
                         ),
                         diff=0, status="INFO"))
    return pd.DataFrame(rows)
