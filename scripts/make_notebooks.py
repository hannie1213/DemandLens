#!/usr/bin/env python3
"""Generate M2's two notebooks (01 inspect raw data, 02 build daily aggregates).

Written with nbformat and then executed with `jupyter nbconvert --execute` to produce
.ipynb files with real outputs. 01 uses the cosmetics shop October file for a raw-structure
check (85 MB, downloads in seconds); 02 demonstrates the aggregation pipeline on the same
file and loads the official daily aggregate table for summary statistics.
"""

from __future__ import annotations

from pathlib import Path

import nbformat as nbf

PROJECT_ROOT = str(Path(__file__).resolve().parents[1])


def code(src: str) -> nbf.v4.new_code_cell:
    return nbf.v4.new_code_cell(src)


def md(src: str) -> nbf.v4.new_markdown_cell:
    return nbf.v4.new_markdown_cell(src)


def build_01() -> nbf.NotebookNode:
    nb = nbf.v4.new_notebook()
    nb.cells = [
        md("# 01 · Raw Data Inspection (M2)\n\n"
           "Inspect the structure, event types, missing values, and date coverage of the raw event CSV. "
           "To reproduce quickly on a normal laptop, this uses the **Cosmetics Shop 2019-Oct** file "
           "(~85 MB compressed) as a demo; the monthly files of the main Multi-category Store dataset are "
           "larger (several GiB) but the inspection procedure is identical. Official figures are in "
           "`reports/tables/aggregation_check.csv` and `reports/aggregation_check_report.md`."),
        md("## Environment"),
        code(
            "import sys\n"
            "from pathlib import Path\n\n"
            "ROOT = Path.cwd()\n"
            "for cand in (ROOT, ROOT.parent, ROOT.parent.parent):\n"
            "    if (cand / 'src' / 'demandlens').exists():\n"
            "        ROOT = cand\n"
            "        break\n"
            "sys.path.insert(0, str(ROOT / 'src'))\n\n"
            "import pandas as pd\n\n"
            "pd.show_versions = None  # keep output clean\n"
            "print('pandas', pd.__version__)"
        ),
        md("## Get the demo raw file\n\n"
           "The public dataset can be downloaded anonymously via kagglehub; it is reused directly when already "
           "cached (requirement D5: switching months only changes config, not code)."),
        code(
            "import kagglehub\n\n"
            "RAW = kagglehub.dataset_download(\n"
            "    'mkechinov/ecommerce-events-history-in-cosmetics-shop',\n"
            "    path='2019-Oct.csv')\n"
            "print('file:', RAW)"
        ),
        md("## Structure: columns, types, first rows"),
        code(
            "head = pd.read_csv(RAW, nrows=5)\n"
            "head"
        ),
        code(
            "sample = pd.read_csv(RAW, usecols=['event_time', 'event_type',\n"
            "                                   'category_id', 'category_code'],\n"
            "                     dtype='string', nrows=2_000_000)\n"
            "sample.dtypes.to_dict()"
        ),
        md("## Event type composition\n\n"
           "Note: this dataset includes `remove_from_cart`, which is **not** one of the three contract types "
           "(view/cart/purchase); it is excluded during aggregation and counted separately."),
        code(
            "sample['event_type'].str.strip().str.lower().value_counts()"
        ),
        md("## Missing values and date coverage"),
        code(
            "date_str = sample['event_time'].str.slice(0, 10)\n"
            "valid_date = pd.to_datetime(date_str, format='%Y-%m-%d', errors='coerce')\n\n"
            "print('category_code missing ratio: %.1f%%' % (sample['category_code'].isna().mean() * 100))\n"
            "print('invalid date rows:', int(valid_date.isna().sum()))\n"
            "print('date range:', valid_date.min(), '..', valid_date.max())\n"
            "print('categories (first 2M rows):', sample['category_id'].nunique())"
        ),
        md("## Contract comparison\n\n"
           "| Checkpoint | Conclusion |\n|---|---|\n"
           "| Column structure | Same shape as Multi-category Store; the reader is reusable |\n"
           "| Event types | Contains out-of-contract types; must be filtered (aggregate.py already handles this) |\n"
           "| category_id | Parsable as integer; usable as the aggregation key |\n"
           "| category_code | Heavily missing; cannot be the key; readable label only |\n\n"
           "A more complete Multi-category Store October inspection (42M events) is in the team's Nov 5 dataset notes; "
           "the pipeline's per-month official figures are in `reports/tables/aggregation_check.csv`."),
    ]
    return nb


def build_02() -> nbf.NotebookNode:
    nb = nbf.v4.new_notebook()
    nb.cells = [
        md("# 02 · Daily Aggregate Build (M2)\n\n"
           "Demonstrates `demandlens.data.aggregate` and actually runs it on a small file, "
           "then loads the official product `daily_all_categories.csv` (Multi-category Store, 7 months, "
           "produced in bulk on this machine by `scripts/build_daily.py`) for a summary check."),
        md("## Pipeline (per assignment 3.5)\n\n"
           "raw event CSV -> chunked read (1M rows/chunk) -> parse time and event type -> "
           "aggregate by date x category -> daily Views / Cart / Purchase -> check statistics. "
           "The consistency invariant is covered by `tests/test_aggregate.py`."),
        code(
            "import sys\n"
            "from pathlib import Path\n\n"
            "ROOT = Path.cwd()\n"
            "for cand in (ROOT, ROOT.parent, ROOT.parent.parent):\n"
            "    if (cand / 'src' / 'demandlens').exists():\n"
            "        ROOT = cand\n"
            "        break\n"
            "sys.path.insert(0, str(ROOT / 'src'))\n\n"
            "import pandas as pd\n"
            "import kagglehub\n"
            "from demandlens.data.aggregate import aggregate_month\n\n"
            "print('ready')"
        ),
        md("## Run aggregation on the demo file"),
        code(
            "RAW = kagglehub.dataset_download(\n"
            "    'mkechinov/ecommerce-events-history-in-cosmetics-shop',\n"
            "    path='2019-Oct.csv')\n"
            "daily, stats = aggregate_month(RAW, chunksize=500_000, progress_every=4)\n"
            "print('raw rows:', f\"{stats['raw_rows']:,}\")\n"
            "print('aggregated rows:', f\"{stats['aggregatable_rows']:,}\")\n"
            "print('contract event counts:', dict(stats['contract_kept']))\n"
            "daily.head()"
        ),
        md("## Aggregation consistency check (D2)\n\n"
           "The count of each event type that entered aggregation must equal the sum of its daily aggregate column."),
        code(
            "checks = {\n"
            "    'view': (stats['contract_kept']['view'], int(daily['views'].sum())),\n"
            "    'cart': (stats['contract_kept']['cart'], int(daily['cart'].sum())),\n"
            "    'purchase': (stats['contract_kept']['purchase'], int(daily['purchase'].sum())),\n"
            "}\n"
            "pd.DataFrame([(k, a, b, b - a) for k, (a, b) in checks.items()],\n"
            "             columns=['event', 'raw_kept', 'aggregated', 'diff'])"
        ),
        md("## Official product: Multi-category Store daily aggregate\n\n"
           "Loads `data/processed/daily_all_categories.csv` (if not yet generated, run "
           "`scripts/run_m2_pipeline.sh` first)."),
        code(
            "from demandlens.data.loader import CONTRACT_EVENTS\n\n"
            "OUT = ROOT / 'data' / 'processed' / 'daily_all_categories.csv'\n"
            "if OUT.exists():\n"
            "    full = pd.read_csv(OUT, parse_dates=['date'])\n"
            "    print('rows:', f'{len(full):,}')\n"
            "    print('dates:', full['date'].min().date(), '..', full['date'].max().date())\n"
            "    print('categories:', full['category_id'].nunique())\n"
            "    print('daily purchase events total/mean:', int(full['purchase'].sum()),\n"
            "          round(full['purchase'].mean(), 1))\n"
            "    print('per-day purchase event distribution:')\n"
            "    per_day = full.groupby('date')['purchase'].sum()\n"
            "    print(per_day.describe().round(1))\n"
            "else:\n"
            "    print('official product not yet generated (multi-month aggregation still running or not run)')"
        ),
        md("## Handoff notes\n\n"
           "- This table **does not zero-fill and does not filter categories** (the M2 product per contract 3.6).\n"
           "- After M3 produces `daily_category.csv` from quality review and category selection, downstream uses only the latter.\n"
           "- Check details: `reports/tables/aggregation_check.csv`; report interpretation: `reports/aggregation_check_report.md`."),
    ]
    return nb


if __name__ == "__main__":
    for name, builder in (("01_inspect_raw.ipynb", build_01), ("02_build_daily.ipynb", build_02)):
        path = Path(PROJECT_ROOT) / "notebooks" / name
        nbf.write(builder(), str(path))
        print("written:", path)
