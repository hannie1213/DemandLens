#!/bin/bash
# M2 background driver: multi-category store 7 months -> cosmetics shop remaining months; per-month download + aggregate, logs to disk
set -u
cd "$(dirname "$0")/.."

echo "=== driver start $(date) ==="
for m in 2019-Oct 2019-Nov 2019-Dec 2020-Jan 2020-Feb 2020-Mar 2020-Apr; do
  echo "--- multi_store $m $(date) ---"
  python3 scripts/build_daily.py --dataset multi_store --months "$m" --project-root . \
    || echo "!!! month $m failed, continue"
done
for m in 2019-Nov 2019-Dec 2020-Jan 2020-Feb 2020-Apr; do
  echo "--- cosmetics $m $(date) ---"
  python3 scripts/build_daily.py --dataset cosmetics --months "$m" --project-root . \
    || echo "!!! cosmetics month $m failed, continue"
done
echo "=== driver done $(date) ==="
