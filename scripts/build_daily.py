#!/usr/bin/env python3
"""M2 main script: download (optional) -> chunked aggregation -> merge -> check -> write to disk.

Usage:
    python3 scripts/build_daily.py --dataset multi_store \
        --months 2019-Oct 2019-Nov --project-root .

- Reuses data already present at data/raw/<dataset>/<month>.csv; otherwise downloads
  anonymously via kagglehub (public dataset, no credentials needed); cache location is
  documented by kagglehub.
- After each month's aggregation, writes data/interim/daily_<dataset>_<month>.csv;
  then merges all months to data/processed/<output name from config> and appends to
  the check table.
- By default deletes the large raw cache after aggregation to free disk (--keep-raw keeps it).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT_DEFAULT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT_DEFAULT / "src"))

from demandlens.data.aggregate import (  # noqa: E402
    aggregate_month,
    build_aggregation_check,
    combine_monthly,
)


def load_config(project_root: Path) -> dict:
    with open(project_root / "config" / "config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def locate_or_download(dataset_key: str, month: str, cfg: dict, project_root: Path) -> Path:
    """Prefer the local raw dir, then the kagglehub cache, downloading anonymously if needed."""
    ds = cfg["datasets"][dataset_key]
    fname = ds["file_pattern"].format(month=month)
    local = project_root / cfg["paths"]["raw_dir"] / dataset_key / fname
    if local.exists():
        return local

    import kagglehub

    # Use the kagglehub cache directly (don't copy large files, to avoid using double disk)
    path = kagglehub.dataset_download(ds["kaggle_slug"], path=fname)
    return Path(path)


def main() -> int:
    ap = argparse.ArgumentParser(description="DemandLens M2: daily aggregate build")
    ap.add_argument("--dataset", required=True,
                    choices=["multi_store", "cosmetics", "retailrocket"])
    ap.add_argument("--months", nargs="+", required=True, help="e.g. 2019-Oct 2020-Apr")
    ap.add_argument("--project-root", type=Path, default=PROJECT_ROOT_DEFAULT)
    ap.add_argument("--keep-raw", action="store_true", help="keep raw large files after aggregation")
    ap.add_argument("--no-download", action="store_true", help="do not download; only process existing files")
    ap.add_argument("--chunksize", type=int, default=None)
    args = ap.parse_args()

    cfg = load_config(args.project_root)
    ds = cfg["datasets"][args.dataset]
    root = args.project_root
    interim = root / cfg["paths"]["interim_dir"]
    processed = root / cfg["paths"]["processed_dir"]
    tables = root / cfg["paths"]["reports_tables_dir"]
    for d in (interim, processed, tables):
        d.mkdir(parents=True, exist_ok=True)

    chunksize = args.chunksize or cfg["aggregation"]["chunksize"]

    month_dailies, month_stats = [], []
    for month in args.months:
        print(f"[{args.dataset}] {month}: locating data file...", flush=True)
        fname = ds["file_pattern"].format(month=month)
        try:
            if args.no_download:
                src = root / cfg["paths"]["raw_dir"] / args.dataset / fname
                if not src.exists():
                    raise FileNotFoundError(f"local file not found and download disabled: {src}")
            else:
                src = locate_or_download(args.dataset, month, cfg, root)
            print(f"  file: {src}", flush=True)
            daily, stats = aggregate_month(src, chunksize=chunksize, progress_every=20)
        except Exception as exc:  # noqa: BLE001 -- a single month failure must not abort the batch; record and continue
            print(f"  !! {month} failed: {type(exc).__name__}: {exc}", flush=True)
            continue

        interim_path = interim / f"daily_{args.dataset}_{month}.csv"
        daily.to_csv(interim_path, index=False)
        month_dailies.append(daily)
        month_stats.append(stats)
        print(f"  daily aggregate {len(daily):,} rows -> {interim_path.name}; "
              f"raw {stats['raw_rows']:,} rows / {stats['file_bytes'] / 2**30:.2f} GiB", flush=True)
        if not args.keep_raw:
            try:
                Path(src).unlink(missing_ok=True)
                print(f"  deleted large cache: {src}", flush=True)
            except OSError:
                pass

    if not month_dailies:
        print("no months to merge; exiting.")
        return 1

    combined, consistency = combine_monthly(month_dailies)
    out_path = processed / ds["output"]
    combined.to_csv(out_path, index=False)
    print(f"merged daily aggregate -> {out_path} ({len(combined):,} rows, "
          f"{combined['date'].nunique()} days x {combined['category_id'].nunique()} categories)")

    check = build_aggregation_check(args.dataset, month_stats, month_dailies, consistency)
    check_path = tables / "aggregation_check.csv"
    if check_path.exists():
        old = pd.read_csv(check_path)
        # Replace only rows for this dataset and this batch of months; keep all other
        # months of this dataset and all other datasets
        touched = set(check["month"])
        keep = old[~((old["dataset"] == args.dataset) & (old["month"].isin(touched)))]
        check = pd.concat([keep, check], ignore_index=True)
    check.to_csv(check_path, index=False)
    n_fail = int((check["status"] == "FAIL").sum())
    print(f"check table -> {check_path} (FAIL rows: {n_fail})")
    return 0 if n_fail == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
