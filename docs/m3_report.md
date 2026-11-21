# Data Quality Category Selection and Time Splitting

Author: [Name and student ID]. Date: 20 November 2026.

We checked the supplied daily tables and prepared category candidates for later model comparison. This section covers data quality, category selection, calendar completion and time splitting. Raw-file loading and aggregation are described in the data preparation section. Features and model results are not included here.

## 1 Data quality audit

### Input scope

The primary dataset is [eCommerce Behavior Data from Multi-category Store](https://www.kaggle.com/datasets/mkechinov/ecommerce-behavior-data-from-multi-category-store). The supplied daily table covers October and November 2019, with 36,555 rows, 61 dates and 691 category IDs. The second dataset is [eCommerce Events History in Cosmetics Shop](https://www.kaggle.com/datasets/mkechinov/ecommerce-events-history-in-cosmetics-shop). Its supplied table covers October 2019 to February 2020, with 63,546 rows, 152 dates and 525 category IDs. These row counts describe daily aggregates rather than raw events.

Both tables contain date, category_id, category_code, views, cart and purchase. Each row represents one category on one UTC date. The prediction target is the number of purchase events, which does not necessarily equal the number of orders or items sold. Category IDs are stored as exact decimal strings during processing to avoid rounding large identifiers.

### Checks and row counts

We checked missing fields, dates, count values, repeated date-category keys, category names, calendar gaps, zero purchases and unusual peaks. No observations were removed, and both input row counts stayed unchanged. Monthly integer-valued text such as 72.0 was converted to an integer in memory. This did not change the row counts or event totals. We did not rewrite the source files.

| Check | Primary | Cosmetics |
|---|---:|---:|
| Rows before and after quality audit | 36,555 → 36,555 | 63,546 → 63,546 |
| Invalid dates | 0 | 0 |
| Missing category IDs | 0 | 0 |
| Invalid event counts | 0 | 0 |
| Missing views/cart/purchase values | 0 / 0 / 0 | 0 / 0 / 0 |
| Repeated date-category keys | 0 | 0 |
| Rows without category_code | 21,913 | 61,360 |
| IDs with no readable code | 414 | 507 |
| IDs with multiple nonempty codes | 0 | 0 |
| Codes shared by multiple IDs | 58 | 3 |
| Observed code depths | 2, 3, 4 | 2, 3 |
| Dates with no site record | 0 | 0 |
| Missing pairs on all-category calendar | 5,596 | 16,254 |
| Observed rows with zero purchases | 12,195 (33.36%) | 15,473 (24.35%) |
| Flagged site-day peaks | 3 | 0 |
| Flagged category purchase-day peaks | 3,247 | 3,202 |

The full calendar combines all observed categories with all dates in the supplied period. Some categories may not have been active throughout that period, so missing pairs do not by themselves indicate a collection failure. Zero-purchase rates are calculated from observed rows only. Code depth measures the number of dot-separated path levels. Since the observed paths have different depths, the categories cannot be assumed to share the same semantic level. Category names are not used to merge IDs, and missing names remain anonymous.

Peak checks use a threshold of median + 10 × median absolute deviation. When the deviation is zero, the threshold becomes 5 × median. This rule identifies values for review rather than proving that they are errors. No flagged values were deleted. The primary site has three flagged dates: November 15, 16 and 17.

### Audit limits

We did not scan the raw event files again. Raw-level checks therefore rely on the supplied aggregation records. Matching retained event fields cannot prove that two records are duplicate events. We did not independently sample raw events or remove records on that basis. Zero repeated daily keys does not mean there are no duplicate raw events.

## 2 Category selection and calendar completion

### Selection basis

We prepared a 10-category candidate and a 20-category candidate. Selection uses development data only and considers history completeness, purchase activity and stable category definitions. Less active categories are also included. We use October 2019 for primary selection and October–November 2019 for cosmetics selection. Later validation and test records do not determine eligibility or ranking.

A category must have a record on every development date, at least seven purchase events in that period and no conflicting nonempty category codes. A missing name does not remove the ID. These rules leave 471 eligible primary categories and 380 eligible cosmetics categories. We chose full development coverage and seven purchases as the thresholds. The assignment does not specify these values.

We rank eligible categories by development purchase count. We then divide them into high, middle and low activity groups with roughly equal numbers of categories. The 10-category candidate takes 6, 3 and 1 from these groups, while the 20-category candidate takes 12, 6 and 2. Selection starts with the highest purchase count within each group. Numeric ID breaks ties and keeps the result repeatable. The quotas avoid selecting only popular categories. The 60/30/10 allocation is our proposed rule, not a ratio shown to be optimal. We retain both candidates for later model comparison.

Development purchase coverage is calculated as the selected categories’ purchase events divided by all purchase events in the same source and development period. This measures the share of observed purchase activity covered by the selection. It does not represent the share of users or future purchases.

| Source | Proposed categories | Development purchase coverage |
|---|---:|---:|
| Primary | 10 | 62.82% |
| Primary | 20 | 71.01% |
| Cosmetics | 10 | 24.37% |
| Cosmetics | 20 | 36.65% |

The four selection tables record each selected ID, purchase total, zero-purchase-day rate, observed days, consecutive history, missing days and activity group. Selected primary categories each have 31 development days, while selected cosmetics categories each have 61. The 20-category set contains the 10-category set and adds six high-activity, three middle-activity and one low-activity categories. These additions follow the group quotas rather than the next ten positions in the overall ranking. The tables prepare both candidates but do not show whether either gives better model performance.

### Calendar results

For each candidate, we create every category-date combination in the source period. Existing counts are copied unchanged. A missing row stays unknown unless source evidence confirms a true zero. Normal site activity alone cannot confirm that a particular category had no events.

| Processing stage (10-category candidate) | Primary rows | Cosmetics rows |
|---|---:|---:|
| Full aggregated daily input | 36,555 | 63,546 |
| After quality audit | 36,555 | 63,546 |
| Observed rows for chosen ten, full period | 610 | 1,449 |
| Calendar rows after completion | 610 | 1,520 |
| Added rows with unknown counts | 0 | 71 |
| Rows filled with confirmed zeros | 0 | 0 |

For the 20-category candidate, the primary input remains 36,555 rows and selection produces 1,220 observed rows without adding dates. The cosmetics input remains 63,546 rows, with 2,969 selected observations out of 3,040 expected category-days. The remaining 71 are unknown and are not exported as daily-contract data.

The primary exports are daily_category.csv for 10 categories and daily_category_top20.csv for 20 categories. They contain 610 and 1,220 observed rows, with continuous dates and nonnegative integer counts. Neither file represents the final choice. Cosmetics has 1,449 of 1,520 expected rows for 10 categories and 2,969 of 3,040 for 20 categories. Both candidates have the same 71 unknown category-days, so no cosmetics daily CSV is exported. All unknowns belong to category 1487580007189447609, whose development history is complete. The missing dates are scattered between December 2019 and February 2020. Their exact dates are stored in gap_review_cosmetics.csv and the run metadata.

We mark unresolved gaps and exclude samples with unknown days in either the input or target period. This follows the assignment rule. We do not invent zero counts or replace categories because of later missingness. A blank-count CSV would violate the daily contract, so it is not supplied for window generation or feature engineering. A complete daily_category_cosmetics.csv is not available. Source evidence is needed to recover the counts or confirm real zeros.

## 3 Time splitting

### Rules and boundaries

We implemented split_by_time and its leakage tests. The prediction origin is the last input day, and the target covers the next seven days. A training target must end strictly before the first validation origin. A validation target must end strictly before the first test origin. Categories in the same source use the same origin grid, with evaluation origins seven days apart. Excluding a missing window does not move the grid. We process the stores separately. For example, the primary validation origin is 2019-10-31 and its target covers 2019-11-01 to 2019-11-07.

| Source | First validation origin | First test origin | Last test origin | Last available date |
|---|---|---|---|---|
| Primary | 2019-10-31 | 2019-11-14 | 2019-11-21 | 2019-11-30 |
| Cosmetics | 2019-11-30 | 2019-12-31 | 2020-02-18 | 2020-02-29 |

The proposed dates are stored in config/config.yaml and evaluation_protocol.md. Both candidate sizes use the same dates within each source. Each source profile contains its own candidate lists and split settings, and there is no primary-only top-level split alias. Window metadata identifies the dataset; a missing or different source identity raises an error. The final count remains unset, while default_count 10 is only a reading convenience. The split protocol must be fixed before model comparison and must not be changed later based on test results.

### Feasibility and tests

The following table reports the number of usable windows for each candidate and input length after unknown input or target days are excluded. These counts audit date metadata only. They do not represent generated features, trained models or prediction results. Detailed category-level records are stored in the run manifest.

| Source | Categories | Input days | Training | Validation | Test |
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

The test suite contains 37 passing checks in tests/test_data.py and tests/test_splits.py. It checks daily values and keys, development-only selection, calendar gaps, strict time boundaries and unknown-window exclusion. Source mismatch and unavailable daily exports are also checked. Feature construction and project integration are outside these tests. The affected cosmetics category has no usable validation or test windows, so its error is unavailable rather than zero.

The primary validation set contains one weekly target period shared by ten or twenty category samples. These samples do not provide ten or twenty independent validation weeks, which limits tuning and model-selection conclusions. Increasing the candidate size adds categories but not evaluation dates. The larger window count should therefore not be treated as additional independent time evidence.

### Limitations

The primary input covers two months, below the formal requirement of at least four months. Under the current boundaries, it produces no 28-day training samples. The longer cosmetics history cannot replace the missing primary history, and both cosmetics candidates still contain 71 unknown category-days. Sparse category names limit interpretation, and neither dataset is established as a Southeast Asian sample.

We will compare both candidate sizes after models are available. Model training and metrics are part of the model evaluation work. The final count should be selected using validation results before final testing. We do not report comparative model results here.

Quality numbers are recorded in reports/tables/quality_report.csv. The four category selection tables contain per-category statistics. Candidate readiness and window counts are in reports/m3_run_manifest.json. Actual run records are in reports/experiment_logs/m3/run_log.md.
