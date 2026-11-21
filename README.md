# DemandLens: Behavior-Based Weekly Purchase Forecasting

This package contains the end-to-end preparation work for DemandLens: data aggregation, quality review, category selection, chronological splitting, exploratory data analysis, sliding-window construction and feature engineering. It includes the supplied monthly aggregates, full daily tables, window-feature datasets, preparation code, tests, reports and two primary-store category candidates. It does not include trained models or a website.

The workflow is:

Raw event files -> monthly daily aggregates -> all-category daily tables -> quality checks -> 10/20-category candidates -> calendar and time-split checks -> exploratory analysis -> sliding windows -> feature engineering.

## 1. Data included

| Dataset | Delivered period | Daily rows | Dates | Category IDs |
|---|---|---:|---:|---:|
| Multi-category Store | October-November 2019 | 36,555 | 61 | 691 |
| Cosmetics Shop | October 2019-February 2020 | 63,546 | 152 | 525 |

Sources:

- [eCommerce Behavior Data from Multi-category Store](https://www.kaggle.com/datasets/mkechinov/ecommerce-behavior-data-from-multi-category-store)
- [eCommerce Events History in Cosmetics Shop](https://www.kaggle.com/datasets/mkechinov/ecommerce-events-history-in-cosmetics-shop)

Each daily row contains date, category_id, category_code, views, cart and purchase. One row represents one category on one UTC date. Counts describe events. Purchase events are not necessarily orders or units sold. Raw event files are not included; dataset licenses and citation requirements must be verified before reuse.

## 2. Candidate outputs

Both 10-category and 20-category candidates are retained for later model comparison. No final category count has been selected. Primary category selection uses October 2019, and cosmetics selection uses October-November 2019. Later validation and test records do not determine category membership.

| Dataset | Categories | Development purchase coverage | Expected rows | Observed rows | Unknown category-days | Published daily table |
|---|---:|---:|---:|---:|---:|---|
| Primary | 10 | 62.82% | 610 | 610 | 0 | daily_category.csv |
| Primary | 20 | 71.01% | 1,220 | 1,220 | 0 | daily_category_top20.csv |
| Cosmetics | 10 | 24.37% | 1,520 | 1,449 | 71 | Not published |
| Cosmetics | 20 | 36.65% | 3,040 | 2,969 | 71 | Not published |

Both primary outputs are in data/processed/. Their dates are continuous and their counts are nonnegative integers. The 20-category set contains the corresponding 10-category set. The filename daily_category.csv does not mean that ten categories have been chosen as the final configuration.

Both cosmetics candidates share 71 unknown dates for category 1487580007189447609. The dates are listed in reports/tables/gap_review_cosmetics.csv. No blank-count cosmetics daily table is exported or supplied for feature generation. Missing counts require source evidence before they can be recovered or confirmed as zeros. Unknown input and target dates are excluded during date-feasibility checks.

## 3. Main files

| File or directory | Content |
|---|---|
| config/config.yaml | Dataset settings, candidate IDs, development periods and source-specific split settings |
| data/interim/ | Supplied monthly daily aggregates |
| data/processed/daily_all_categories.csv | All-category primary daily table |
| data/processed/daily_all_categories_cosmetics.csv | All-category cosmetics daily table |
| data/processed/daily_category.csv | Primary ten-category table |
| data/processed/daily_category_top20.csv | Primary twenty-category table |
| reports/tables/aggregation_check.csv | Supplied aggregation counters and consistency checks |
| reports/tables/quality_report.csv | Quality metrics and candidate statistics |
| reports/tables/category_selection.csv | Primary ten-category selection |
| reports/tables/category_selection_top20.csv | Primary twenty-category selection |
| reports/tables/category_selection_cosmetics.csv | Cosmetics ten-category selection |
| reports/tables/category_selection_cosmetics_top20.csv | Cosmetics twenty-category selection |
| reports/tables/gap_review_cosmetics.csv | Unresolved dates shared by both cosmetics candidates |
| reports/m3_run_manifest.json | Candidate readiness, output paths, unknown days and window counts |
| reports/experiment_logs/m2/ | Aggregation run logs |
| reports/experiment_logs/m3/run_log.md | Quality and split execution record |
| reports/aggregation_check_report.md | Aggregation check report |
| docs/data_dictionary.md | Field definitions |
| docs/report_m2_dataset.md | Dataset and aggregation report material |
| docs/m3_report.md | Quality, category selection and time-splitting report |
| docs/evaluation_protocol.md | Category and split protocol |
| notebooks/01_inspect_raw.ipynb | Raw-data inspection notebook |
| notebooks/02_build_daily.ipynb | Daily aggregation notebook |
| notebooks/02b_quality_and_selection.ipynb | Executed quality, category and date audit |
| scripts/build_daily.py | Original source reading and aggregation entry point |
| scripts/select_categories.py | Preparation of both candidate sizes |
| src/demandlens/data/ | Reading, aggregation, quality and category/calendar functions |
| src/demandlens/evaluation/splits.py | Time splitting and date-feasibility checks |
| tests/test_aggregate.py | Aggregation tests |
| tests/test_data.py | Quality and category/calendar tests |
| tests/test_splits.py | Time-boundary and leakage tests |
| src/demandlens/features/windows.py | Sliding-window construction and collection-gap handling |
| src/demandlens/features/build_features.py | Feature engineering with the E2/E3 ablation switches |
| scripts/build_windows.py | Batch window export for lookback 7/14/28 |
| scripts/build_features.py | Batch feature export |
| scripts/run_eda.py | Exploratory data analysis (five figures) |
| data/processed/windows_lookback7.csv | 7-day window-feature dataset |
| data/processed/windows_lookback14.csv | 14-day window-feature dataset |
| data/processed/windows_lookback28.csv | 28-day window-feature dataset |
| docs/feature_dictionary.md | Feature name, meaning, formula and date range |
| tests/test_windows_leakage.py | Window and feature leakage tests |
| notebooks/03_eda.ipynb | Exploratory data analysis notebook |
| notebooks/04_features_windows.ipynb | Window and feature notebook |
| requirements.txt | Pinned dependencies for the whole pipeline |

The package also contains aggregation helper scripts and preliminary split documents. The preliminary dates are earlier drafts. Use the source-specific settings in config/config.yaml and docs/evaluation_protocol.md for current preparation.

## 4. Run the supplied preparation

Open a terminal in the demandlens project root, where README.md, config/, src/ and scripts/ are located. The submitted preparation was checked using Python 3.10. The commands below use PowerShell.

```powershell
python -m pip install -r requirements.txt
$env:PYTHONPATH = (Join-Path $PWD 'src')

# Run all included tests.
python -m pytest tests -v

# Prepare both datasets and both candidate counts.
python scripts/select_categories.py

# Require complete daily data for both primary candidates.
python scripts/select_categories.py --dataset multi_store --require-ready

# Expected nonzero exit while cosmetics dates remain unresolved.
python scripts/select_categories.py --dataset cosmetics --require-ready

# Build sliding-window datasets for lookback 7, 14 and 28 days.
python scripts/build_windows.py

# Build the feature datasets (purchase + behavior + calendar + category one-hot).
python scripts/build_features.py

# Generate the five exploratory data analysis figures.
python scripts/run_eda.py
```

The submitted archive was checked with 57 passing tests: seven aggregation checks, 37 quality/split checks and 13 window/feature leakage checks. The code cells in notebooks 02b and 04 also executed successfully. Raw aggregation was not rerun because original event files are not included.

The standard preparation command succeeds and records cosmetics as unavailable for daily export. The cosmetics --require-ready command intentionally exits nonzero with PENDING_M2_GAP_EVIDENCE. This distinguishes a completed audit from a complete daily dataset. Audit results are still saved; unknown counts are not silently filled with zeros.

On bash-compatible systems, set the source path with `export PYTHONPATH="$PWD/src"` instead of the PowerShell assignment.

## 5. Optional raw-data aggregation

The delivered monthly and daily tables are sufficient to rerun the quality and category preparation. Raw rebuilding is separate and is not required for this check.

If original CSVs are available, place primary files under data/raw/multi_store/, using names such as 2019-Oct.csv. To process local files without downloading or deleting them:

```powershell
python scripts/build_daily.py --dataset multi_store --months 2019-Oct 2019-Nov --project-root . --no-download --keep-raw
```

The aggregation stage keeps view, cart and purchase. Other event types are counted separately. Invalid dates and category IDs are excluded and counted. Missing category-date combinations are not filled with zero at this stage. Downloads, when used, require the original downloader dependencies and suitable source access. Preserve or back up delivered outputs before rebuilding, because the aggregation script rewrites the requested dataset's outputs.

## 6. Configuration and downstream use

Read candidate IDs and output names from m3.sources.<source>.variants in config/config.yaml, using source multi_store or cosmetics and candidate key '10' or '20'. Each source has its own split profile. There is no primary-only top-level split alias.

The prediction origin is the final input day. For example, origin 2019-10-31 predicts 2019-11-01 to 2019-11-07. Training targets must end strictly before the first validation origin. Validation targets must end strictly before the first test origin. Evaluation origins are seven days apart. Both candidate sizes use the same dates within each source.

Window metadata must include dataset matching the chosen split profile. Call split_by_time(meta, cfg['m3']['sources'][source]['split'], unknown_days). Missing or mismatched source identity raises an error. Actual feature and window construction is separate from the date audit.

The run manifest is used by notebook 02b and records both candidates under datasets.<source>.variants. Check output_file before reading a candidate table: null means no complete daily table is published. The helper read_candidate_daily(project_root, candidate) raises a clear error for unavailable data. Source-level default_count 10 is a convenience view, not a final choice.

Preserve m3.sources when integrating or freezing the configuration. If a different runtime configuration omits preparation profiles, use --config PATH with a complete preparation configuration. --require-approved checks full protocol approval, which is separate from the confirmed arrangement to compare both category counts.

## 7. Current limitations

- Primary history covers two months, below the formal requirement of at least four months. Its present split has one validation week and no 28-day training samples.
- Ten or twenty category samples from the same validation week are not independent validation weeks. Model tuning conclusions will be limited.
- Cosmetics has 71 unresolved selected category-days and no published complete candidate daily tables. Its longer history does not replace missing primary months.
- Matching retained event fields cannot establish true duplicate raw events. Independent raw-event sampling and source completeness are not verified here.
- Sparse category names limit interpretation. Neither dataset is established as a Southeast Asian sample.
- Final category-count selection and model comparison remain future work. Selection should use validation results before final testing.

The included report still requires the author's real name and student ID. The personal contribution appendix and actual Git evidence must be supplied separately for the final personal submission. They are not included in this archive. System metadata and caches such as __MACOSX, .DS_Store, .pytest_cache and __pycache__ are not required project files.
