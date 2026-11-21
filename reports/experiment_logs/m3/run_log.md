# Data quality and time split execution log

Execution date: 20 November 2026. Input: the supplied M2 archive, using delivered monthly and full daily tables. Original observations were not edited. Both candidate counts are retained for later model comparison.

## Inputs and preparation

| Source | Input rows | Dates | Category IDs | Used months |
|---|---:|---:|---:|---|
| Primary | 36,555 | 61 | 691 | October–November 2019 |
| Cosmetics | 63,546 | 152 | 525 | October 2019–February 2020 |

Quality audit removes zero rows. Monthly integer-valued decimal text is normalized in memory only. No unknown counts are filled without evidence. Development selection uses October for primary and October–November for cosmetics.

## Monthly counter check

As a supporting input audit, six primary and fifteen cosmetics month/event totals were recomputed from delivered aggregates and matched the supplied counters. This is not an independent raw-file scan or a replacement for the upstream aggregation test. Primary totals: views 104,335,509; cart 3,955,446; purchase 1,659,788. Cosmetics: views 9,657,821; cart 5,768,333; purchase 1,287,007. No true raw-event deduplication is claimed.

## Candidate results

| Source | Count | Development purchase coverage | Observed rows | Expected calendar | Unknown days |
|---|---:|---:|---:|---:|---:|
| Primary | 10 | 62.82% | 610 | 610 | 0 |
| Primary | 20 | 71.01% | 1,220 | 1,220 | 0 |
| Cosmetics | 10 | 24.37% | 1,449 | 1,520 | 71 |
| Cosmetics | 20 | 36.65% | 2,969 | 3,040 | 71 |

Both primary tables satisfy the integer daily contract. Cosmetics exports are withheld. The shared gap list covers the same 71 category-days in both candidates. The run manifest stores both candidates' unknown-day maps.

## Date feasibility after unknown-day exclusion

| Source | Count | Lookback | Train | Validation | Test |
|---|---:|---:|---:|---:|---:|
| multi_store | 10 | 7 | 170 | 10 | 20 |
| multi_store | 10 | 14 | 100 | 10 | 20 |
| multi_store | 10 | 28 | 0 | 10 | 20 |
| multi_store | 20 | 7 | 340 | 20 | 40 |
| multi_store | 20 | 14 | 200 | 20 | 40 |
| multi_store | 20 | 28 | 0 | 20 | 40 |
| cosmetics | 10 | 7 | 470 | 36 | 72 |
| cosmetics | 10 | 14 | 400 | 36 | 72 |
| cosmetics | 10 | 28 | 260 | 36 | 72 |
| cosmetics | 20 | 7 | 940 | 76 | 152 |
| cosmetics | 20 | 14 | 800 | 76 | 152 |
| cosmetics | 20 | 28 | 520 | 76 | 152 |

These are calendar audits, not actual feature or model runs. Primary validation comprises one weekly target interval: ten or twenty category samples are not ten or twenty independent time periods. Tuning conclusions would be weak. Primary 28-day training has zero samples. Both issues require a scope/data decision before formal experiments.

## Executed checks

- python scripts/select_categories.py: success, both sources and both counts audited.
- python -m pytest tests/test_data.py tests/test_splits.py -q -p no:cacheprovider: 37 passed.
- notebooks/02b_quality_and_selection.ipynb: three code cells executed.
- Source-identity regression: wrong or missing dataset metadata raises a clear error for configured source splits.
- Unavailable candidate regression: safe reader raises a descriptive ValueError instead of constructing a null path.

### Readiness command: multi_store

Command: python scripts/select_categories.py --dataset multi_store --require-ready

Actual exit code: 0. Expected success.

```text
{
  "multi_store": {
    "status": "complete_observed_candidate_not_final_selection",
    "output": "data/processed/daily_category.csv",
    "rows": 610,
    "unknown_days": 0
  }
}
```

### Readiness command: cosmetics

Command: python scripts/select_categories.py --dataset cosmetics --require-ready

Actual exit code: 1. Expected failure because daily exports remain unavailable.

```text
{
  "cosmetics": {
    "status": "withheld_unresolved_gaps_no_daily_contract_output",
    "output": null,
    "rows": 1520,
    "unknown_days": 71
  }
}
PENDING_M2_GAP_EVIDENCE: no final cosmetics daily table is claimed
```

## Remaining items

Final category count awaits later validation comparison. Source gaps, insufficient primary history and full protocol freezing remain open. Personal identity and Git records are outside this execution log. Feature generation, fitted models and evaluation scores were not run.
