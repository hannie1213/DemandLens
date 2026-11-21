#!/usr/bin/env python3
"""M2 draft: preliminary time-split proposal (final boundaries reviewed by M3 and frozen in config.yaml).

Rules (per assignment 4.6):
- Strict time order train -> val -> test; all categories of the same UTC day share one partition.
- Split boundaries on whole months: last 2 calendar months = test, the month before = val, rest = train.
- Within val/test, evaluate over non-overlapping 7-day forecast intervals (contiguous 7-day blocks
  from the partition start); trailing days shorter than 7 are not evaluated (eval_block_start empty).
- No test-period information is introduced (calendar dates only; no numeric distribution is inspected).

Usage:
    python3 scripts/make_preliminary_split.py [--dataset multi_store]
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

LOOKBACK_MAX = 28  # longest input window (E4 compares 7/14/28), used to check first-window feasibility


def month_start(d: date) -> date:
    return d.replace(day=1)


def shift_months(d: date, k: int) -> date:
    m = d.month - 1 + k
    return date(d.year + m // 12, m % 12 + 1, 1)


def seven_day_blocks(start: date, end: date) -> list[tuple[date, date]]:
    """Contiguous 7-day blocks inside [start, end] starting at start; keep only complete blocks."""
    blocks = []
    b = start
    while b + timedelta(days=6) <= end:
        blocks.append((b, b + timedelta(days=6)))
        b += timedelta(days=7)
    return blocks


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="multi_store")
    ap.add_argument("--output-name", default=None,
                    help="default: multi_store -> preliminary_split.csv, else -> preliminary_split_<dataset>.csv")
    args = ap.parse_args()

    processed = PROJECT_ROOT / "data" / "processed"
    src = processed / ("daily_all_categories.csv" if args.dataset == "multi_store"
                       else f"daily_all_categories_{args.dataset}.csv")
    if not src.exists():
        print(f"daily aggregate not found; run scripts/build_daily.py first: {src}")
        return 1

    daily = pd.read_csv(src, usecols=["date"])
    dates = sorted({date.fromisoformat(d) for d in daily["date"].unique()})
    d_min, d_max = dates[0], dates[-1]
    months = sorted({month_start(d) for d in dates})

    if len(months) >= 4:
        # Rule A: last 2 whole months test, the month before val, the rest train
        val_month = months[-3]
        val_start = val_month
        val_end = shift_months(val_month, 1) - timedelta(days=1)
        test_start = shift_months(val_month, 1)
        test_end = d_max
        train_until = val_start - timedelta(days=1)
    elif len(months) == 3:
        # Rule B: m1 train, m2 val, m3 test
        val_start = months[1]
        val_end = months[2] - timedelta(days=1)
        test_start = months[2]
        test_end = d_max
        train_until = months[1] - timedelta(days=1)
    else:
        # Rule C (2 months): m1 train, first 14 days of m2 val, the rest test.
        # Evaluation coverage is limited (val/test each have only 2 complete 7-day blocks);
        # re-split with Rule A once more months are available.
        val_start = months[1]
        val_end = months[1] + timedelta(days=13)
        test_start = months[1] + timedelta(days=14)
        test_end = d_max
        train_until = months[1] - timedelta(days=1)

    val_blocks = seven_day_blocks(val_start, val_end)
    test_blocks = seven_day_blocks(test_start, test_end)

    rows = []
    for d in dates:
        if d <= train_until:
            split = "train"
        elif d <= val_end:
            split = "val"
        else:
            split = "test"
        block = None
        if split == "val":
            for bs, be in val_blocks:
                if bs <= d <= be:
                    block = bs.isoformat()
        elif split == "test":
            for bs, be in test_blocks:
                if bs <= d <= be:
                    block = bs.isoformat()
        rows.append(dict(date=d.isoformat(), split=split, eval_block_start=block or ""))

    out = pd.DataFrame(rows)
    out_dir = PROJECT_ROOT / "reports" / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)
    name = args.output_name or ("preliminary_split.csv" if args.dataset == "multi_store"
                                else f"preliminary_split_{args.dataset}.csv")
    out_path = out_dir / name
    out.to_csv(out_path, index=False)

    first_train_forecast_start = d_min + timedelta(days=LOOKBACK_MAX)
    n_train_days = int((out["split"] == "train").sum())
    n_val_eval_days = int((out["split"] == "val").sum() and out.loc[out["split"] == "val", "eval_block_start"].ne("").sum())
    n_test_eval_days = int(out.loc[out["split"] == "test", "eval_block_start"].ne("").sum())
    print(f"date range: {d_min} .. {d_max} ({len(dates)} days, {len(months)} calendar months)")
    print(f"train: {d_min} .. {train_until} ({n_train_days} days)")
    print(f"val:   {val_start} .. {val_end}, {len(val_blocks)} complete eval weeks"
          f" (covers {n_val_eval_days} days)")
    print(f"test:  {test_start} .. {test_end}, {len(test_blocks)} complete eval weeks"
          f" (covers {n_test_eval_days} days)")
    print(f"with longest input window {LOOKBACK_MAX} days, earliest valid forecast origin in train: "
          f"{first_train_forecast_start}")
    print(f"draft -> {out_path} (M3 reviews and freezes the boundaries into config/config.yaml)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
