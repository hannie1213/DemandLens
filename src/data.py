"""data.py — Data loading, daily aggregation, quality checks, category selection.

Owner: M2

This module defines the data interface. The function signatures below are the
contract; implementations are TODO.

Daily table schema (agreed):
    date (UTC day), category_id, category_name, views, cart, purchase.
"""

from __future__ import annotations

import pandas as pd


def read_raw_chunks(path: str, usecols: list[str] | None = None, chunksize: int = 1_000_000):
    """Yield the raw event log in chunks, keeping only the needed columns.

    TODO: implement.
    """
    raise NotImplementedError


def build_daily_table(events: pd.DataFrame) -> pd.DataFrame:
    """Aggregate events into date x category_id x event_type counts, then pivot
    to a wide table with columns views, cart, purchase.

    TODO: implement. Must assert that aggregated totals match raw counts.
    """
    raise NotImplementedError


def run_quality_checks(events: pd.DataFrame) -> dict:
    """Report duplicate rows (sampled estimate), zero prices, missing
    category_code/brand, etc.

    TODO: implement.
    """
    raise NotImplementedError


def select_categories(daily: pd.DataFrame, n: int = 20) -> pd.DataFrame:
    """Select categories with records on all dates, then top-N by purchase count.

    TODO: implement. Report the share of total purchases covered.
    """
    raise NotImplementedError


def fill_calendar(daily: pd.DataFrame) -> pd.DataFrame:
    """Complete the calendar for selected categories; fill missing days with 0
    only after confirming normal collection that day.

    TODO: implement.
    """
    raise NotImplementedError
