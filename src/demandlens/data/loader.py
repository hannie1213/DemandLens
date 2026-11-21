"""Read the raw event CSV in chunks (requirement D1: a single month file is processable on a normal
laptop without loading it all at once).

Only the columns needed by the contract are kept: event_time, event_type, category_id, category_code.
user_id / user_session / product_id / brand / price are not used in the first version (assignment 3.1).
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pandas as pd

USECOLS = ["event_time", "event_type", "category_id", "category_code"]

DTYPES = {
    "event_time": "string",
    "event_type": "string",
    "category_id": "string",
    "category_code": "string",
}

# The contract (3.6) only aggregates these three event types; remove_from_cart etc. are counted separately and do not enter the daily aggregate.
CONTRACT_EVENTS = ("view", "cart", "purchase")

DEFAULT_CHUNKSIZE = 1_000_000


def iter_event_chunks(
    path: str | Path,
    chunksize: int = DEFAULT_CHUNKSIZE,
    usecols: list[str] | None = None,
) -> Iterator[pd.DataFrame]:
    """Yield DataFrames containing only the contract columns, chunk by chunk.

    Raise a clear error when columns are missing (more readable than pandas' default ValueError).
    """
    cols = list(usecols) if usecols is not None else list(USECOLS)
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"raw event file not found: {path}")
    reader = pd.read_csv(
        path,
        usecols=cols,
        dtype={c: DTYPES[c] for c in cols},
        chunksize=chunksize,
    )
    yield from reader


def raw_month_size(path: str | Path) -> int:
    """Raw file size in bytes (written to the check table for reproducible scale notes)."""
    return Path(path).stat().st_size
