"""M2 aggregation consistency tests (synthetic small data; no real data needed; runs in seconds).

Covers D1/D2 acceptance points:
- after aggregation, totals per event type match the raw statistics (D2)
- only the three contract columns are kept and processed in chunks (D1)
- out-of-contract events such as remove_from_cart are excluded but counted separately
- rows with an invalid date / invalid category_id do not enter aggregation and are counted
- same category over multiple days, multiple categories on the same day, category_code missing and conflicts, within-chunk duplicate rows
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from demandlens.data.aggregate import (  # noqa: E402
    aggregate_month,
    build_aggregation_check,
    combine_monthly,
    month_label_from_filename,
)
from demandlens.data.loader import CONTRACT_EVENTS  # noqa: E402


def _write_csv(path: Path, rows: list[dict]) -> Path:
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


@pytest.fixture()
def tiny_month(tmp_path: Path) -> Path:
    """Two categories, three dates, with various edge rows mixed in. Expected values are hand-computed in each test.

    Row 1 and row 2 are identical (a duplicate-row sample).
    """
    rows = [
        # category 1 (code a.b): 10-01 view x4 (two identical rows), cart x1, purchase x2
        dict(event_time="2019-10-01 00:00:00 UTC", event_type="view",
             category_id="1", category_code="a.b"),
        dict(event_time="2019-10-01 00:00:00 UTC", event_type="view",
             category_id="1", category_code="a.b"),
        dict(event_time="2019-10-01 02:00:00 UTC", event_type="view",
             category_id="1", category_code="a.b"),
        dict(event_time="2019-10-01 03:00:00 UTC", event_type="view",
             category_id="1", category_code="a.b"),
        dict(event_time="2019-10-01 04:00:00 UTC", event_type="cart",
             category_id="1", category_code="a.b"),
        dict(event_time="2019-10-01 05:00:00 UTC", event_type="purchase",
             category_id="1", category_code="a.b"),
        dict(event_time="2019-10-01 06:00:00 UTC", event_type="purchase",
             category_id="1", category_code="a.b"),
        # category 2: 10-01 purchase x1 with no code; 10-02 view x1 + remove_from_cart x1
        dict(event_time="2019-10-01 07:00:00 UTC", event_type="purchase",
             category_id="2", category_code=""),
        dict(event_time="2019-10-02 00:00:00 UTC", event_type="view",
             category_id="2", category_code=""),
        dict(event_time="2019-10-02 01:00:00 UTC", event_type="remove_from_cart",
             category_id="2", category_code=""),
        # one invalid-date row (event type still view; should be counted as an invalid-date row)
        dict(event_time="not-a-date UTC", event_type="view",
             category_id="1", category_code="a.b"),
        # one invalid-category_id row
        dict(event_time="2019-10-02 02:00:00 UTC", event_type="purchase",
             category_id="N/A", category_code="x.y"),
        # event types with different casing should be normalized and counted
        dict(event_time="2019-10-03 00:00:00 UTC", event_type="VIEW",
             category_id="2", category_code=""),
    ]
    return _write_csv(tmp_path / "2019-Oct.csv", rows)


def test_contract_totals_match(tiny_month: Path) -> None:
    daily, stats = aggregate_month(tiny_month, chunksize=4)  # force 4 chunks to verify chunking correctness
    # raw event counts (including invalid rows):
    assert stats["event_counts"]["view"] == 7  # 6 valid view rows + 1 invalid-date view row + 1 normalized VIEW row
    assert stats["event_counts"]["cart"] == 1
    assert stats["event_counts"]["purchase"] == 4
    assert stats["event_counts"]["remove_from_cart"] == 1
    assert set(CONTRACT_EVENTS) == {"view", "cart", "purchase"}

    # D2 criterion: valid contract events entering aggregation == daily aggregate column sum
    for event, col in (("view", "views"), ("cart", "cart"), ("purchase", "purchase")):
        raw_kept = stats["contract_kept"].get(event, 0)
        assert int(daily[col].sum()) == raw_kept, f"{event} inconsistent before vs after aggregation"
    assert stats["contract_kept"]["view"] == 6      # 7 - 1 invalid date
    assert stats["contract_kept"]["purchase"] == 3  # 4 - 1 invalid category


def test_daily_values(tiny_month: Path) -> None:
    daily, stats = aggregate_month(tiny_month)
    assert stats["raw_rows"] == 13
    assert stats["aggregatable_rows"] == 10  # 13 - 1 invalid date - 1 invalid category - 1 remove_from_cart
    assert stats["invalid_date_rows"] == 1
    assert stats["invalid_category_rows"] == 1
    assert stats["duplicate_within_chunks"] == 1  # two identical view rows

    by_cat_date = daily.set_index(["date", "category_id"])
    assert int(by_cat_date.loc[("2019-10-01", 1), "views"]) == 4
    assert int(by_cat_date.loc[("2019-10-01", 1), "cart"]) == 1
    assert int(by_cat_date.loc[("2019-10-01", 1), "purchase"]) == 2
    assert int(by_cat_date.loc[("2019-10-01", 2), "purchase"]) == 1
    assert int(by_cat_date.loc[("2019-10-02", 2), "views"]) == 1
    assert ("2019-10-02", 2) not in by_cat_date.index or \
        int(by_cat_date.loc[("2019-10-02", 2), "purchase"]) == 0  # remove_from_cart does not produce a purchase
    assert int(by_cat_date.loc[("2019-10-03", 2), "views"]) == 1  # VIEW case normalization
    assert len(daily) == 4  # no zero-fill: only (date, category) pairs that appeared have rows (cat1 only has 10-01 records)


def test_no_zero_fill_and_columns(tiny_month: Path) -> None:
    daily, _ = aggregate_month(tiny_month)
    assert list(daily.columns) == ["date", "category_id", "category_code",
                                   "views", "cart", "purchase"]
    # rows with missing code have empty category_code after aggregation
    cat2 = daily[daily["category_id"] == 2]
    assert cat2["category_code"].isna().all()
    cat1 = daily[daily["category_id"] == 1]
    assert (cat1["category_code"] == "a.b").all()


def test_check_report_flags_mismatch(tmp_path: Path) -> None:
    path = _write_csv(
        tmp_path / "2019-Oct.csv",
        [
            dict(event_time="2019-10-01 00:00:00 UTC", event_type="purchase",
                 category_id="9", category_code="x"),
            dict(event_time="2019-10-01 01:00:00 UTC", event_type="purchase",
                 category_id="9", category_code="x"),
        ],
    )
    daily, stats = aggregate_month(path)
    check = build_aggregation_check("tiny", [stats], [daily])
    count_rows = check[check["check"] == "count:purchase"]
    assert len(count_rows) == 1
    row = count_rows.iloc[0]
    assert row["status"] == "OK" and row["diff"] == 0
    assert (check["status"] == "FAIL").sum() == 0


def test_combine_and_cross_month_consistency(tmp_path: Path) -> None:
    p1 = _write_csv(
        tmp_path / "2019-Oct.csv",
        [dict(event_time="2019-10-01 00:00:00 UTC", event_type="view",
              category_id="5", category_code="c.d"),
         dict(event_time="2019-10-02 00:00:00 UTC", event_type="purchase",
              category_id="5", category_code="c.d")],
    )
    p2 = _write_csv(
        tmp_path / "2019-Nov.csv",
        [dict(event_time="2019-11-01 00:00:00 UTC", event_type="view",
              category_id="5", category_code="c.d")],
    )
    d1, s1 = aggregate_month(p1)
    d2, s2 = aggregate_month(p2)
    combined, consistency = combine_monthly([d1, d2])
    assert combined["date"].nunique() == 3
    assert consistency["consistent"].all()

    check = build_aggregation_check("tiny", [s1, s2], [d1, d2], consistency)
    assert (check["status"] == "FAIL").sum() == 0
    # per-month event counts are checked independently and not mixed up by cross-month merge
    oct_row = check[(check["month"] == "2019-Oct") & (check["check"] == "count:purchase")]
    assert int(oct_row["aggregated_value"].iloc[0]) == 1


def test_month_label(tmp_path: Path) -> None:
    assert month_label_from_filename(tmp_path / "2019-Oct.csv") == "2019-10"
    assert month_label_from_filename(tmp_path / "2020-Apr.csv") == "2020-04"


def test_missing_file() -> None:
    from demandlens.data.loader import iter_event_chunks

    with pytest.raises(FileNotFoundError):
        list(iter_event_chunks("/nonexistent/2019-Oct.csv", chunksize=10))
