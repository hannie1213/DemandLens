#!/usr/bin/env python3
"""Merge all monthly daily aggregates for one dataset in data/interim/ into the final
product and re-check against the check table.

build_daily.py writes only the current month to processed when run month-by-month;
this script does the final merge:
- merge all interim daily aggregates -> data/processed/<output> (overwrite)
- reconcile against the monthly count:{event} rows in aggregation_check.csv
- verify the merged table has unique (date, category_id)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from demandlens.data.aggregate import combine_monthly  # noqa: E402

OUTPUT_NAMES = {
    "multi_store": "daily_all_categories.csv",
    "cosmetics": "daily_all_categories_cosmetics.csv",
    "retailrocket": "daily_all_categories_retailrocket.csv",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True, choices=sorted(OUTPUT_NAMES))
    args = ap.parse_args()

    interim = PROJECT_ROOT / "data" / "interim"
    parts = sorted(interim.glob(f"daily_{args.dataset}_*.csv"))
    if not parts:
        print(f"no monthly files for {args.dataset} in interim")
        return 1

    monthly = [pd.read_csv(p, dtype={"date": "string"}) for p in parts]
    combined, consistency = combine_monthly(monthly)
    out_path = PROJECT_ROOT / "data" / "processed" / OUTPUT_NAMES[args.dataset]
    combined.to_csv(out_path, index=False)

    n_dup = int(combined.duplicated(["date", "category_id"]).sum())
    print(f"merged {len(parts)} months -> {out_path.name}: {len(combined):,} rows, "
          f"{combined['date'].nunique()} days x {combined['category_id'].nunique()} categories, "
          f"duplicate (date,category) rows: {n_dup}")
    n_bad_codes = int((~consistency["consistent"]).sum())
    print(f"categories with inconsistent category_code across months: {n_bad_codes}")

    check_path = PROJECT_ROOT / "reports" / "tables" / "aggregation_check.csv"
    if check_path.exists():
        check = pd.read_csv(check_path)
        sub = check[(check["dataset"] == args.dataset) & (check["status"] == "OK")]
        bad = 0
        for p in parts:
            month = p.stem.replace(f"daily_{args.dataset}_", "")
            d = pd.read_csv(p, usecols=["views", "cart", "purchase"])
            for event, col in (("view", "views"), ("cart", "cart"), ("purchase", "purchase")):
                rows = sub[(sub["month"] == month) & (sub["check"] == f"count:{event}")]
                if len(rows) and int(rows["raw_value"].iloc[0]) != int(d[col].sum()):
                    print(f"!! {month} {event}: check table {rows['raw_value'].iloc[0]} "
                          f"!= interim sum {int(d[col].sum())}")
                    bad += 1
        print("monthly reconciliation: " + ("all consistent" if bad == 0 else f"{bad} mismatches"))
        return 0 if bad == 0 and n_dup == 0 else 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
