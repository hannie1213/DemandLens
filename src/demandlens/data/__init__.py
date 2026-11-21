"""DemandLens data layer: M2 read and aggregation modules."""

from demandlens.data.loader import iter_event_chunks
from demandlens.data.aggregate import aggregate_month, combine_monthly, build_aggregation_check

__all__ = [
    "iter_event_chunks",
    "aggregate_month",
    "combine_monthly",
    "build_aggregation_check",
]
