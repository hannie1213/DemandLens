# M3 category and time split protocol

## Confirmed comparison arrangement

On 20 November 2026, the user confirmed M1's arrangement to retain both 10-category and 20-category candidates and compare them after models are available. Neither count is the final choice. This confirmation does not assert approval of every threshold or date. The full protocol freeze remains pending. Model comparisons belong to M5/M6; final category count must be chosen using validation results before final test evaluation.

## Development-only category selection

Primary selection uses 2019-10-01 through 2019-10-31. Cosmetics selection uses 2019-10-01 through 2019-11-30. Eligibility requires complete observed development dates, at least seven purchase events and no conflicting nonempty category codes. Anonymous IDs remain eligible. There are 471 and 380 eligible categories respectively.

Eligible IDs are purchase-ranked with numeric-ID tie breaking and divided into equal-count activity thirds. The 10-category candidate takes 6/3/1 from high/middle/low thirds; the 20-category candidate takes 12/6/2. These numeric thresholds and quotas are implementation rules, not assignment-specified constants or proven optimal settings. No held-out values or gaps decide membership.

| Source | Candidate count | Development purchase coverage | Expected rows | Observed rows | Unknown dates | Daily export |
|---|---:|---:|---:|---:|---:|---|
| Primary | 10 | 62.82% | 610 | 610 | 0 | daily_category.csv |
| Primary | 20 | 71.01% | 1,220 | 1,220 | 0 | daily_category_top20.csv |
| Cosmetics | 10 | 24.37% | 1,520 | 1,449 | 71 | withheld |
| Cosmetics | 20 | 36.65% | 3,040 | 2,969 | 71 | withheld |

Coverage uses all development purchase events in the same source as denominator. Candidate IDs are in config/config.yaml under m3.sources.<source>.variants. Primary-only root split/categories aliases are omitted. Default_count 10 is a convenience view only, not the selected winner. The top20 filenames identify candidate size, not a pure popularity-top-20 rule.

## Calendar contract

Observed zero counts are valid; absent category-days are unknown. Only confirmed_zero evidence with a reference and reviewer may justify zero filling. No unknown is exported as a blank count in a daily-contract table. Cosmetics daily exports are withheld for both candidates. Both have the same 71 unresolved dates for ID 1487580007189447609, listed once in gap_review_cosmetics.csv. The run manifest contains each candidate's unknown-day map and window feasibility. That metadata is not a training daily table. Source evidence is needed to recover a complete cosmetics daily output. Do not replace a category based on later availability.

## Time splitting

Origin t is the last input day. The target spans t+1 through t+7. A training target must end strictly before the first validation origin; a validation target must end strictly before the first test origin. Categories share a weekly evaluation grid within each source. Test targets do not overlap. Exclude any input or target interval that includes an unknown day. Unknown-day exclusion is required by assignment section 3.7.

| Source | First validation origin | First test origin | Last test origin | Last data date |
|---|---|---|---|---|
| Primary | 2019-10-31 | 2019-11-14 | 2019-11-21 | 2019-11-30 |
| Cosmetics | 2019-11-30 | 2019-12-31 | 2020-02-18 | 2020-02-29 |

Both candidate sizes use the same source-specific dates and rules. split_by_time accepts one source profile and that candidate's unknown-day map. It returns positional partitions, not features or model scores. M4 owns actual window/feature generation; M1 owns integration. Primary two-month history yields no 28-day training samples under these rules and does not meet the formal four-month requirement. Cosmetics does not replace missing primary months.

## Scope of handoff

M3 supplies candidate tables, contract-compliant primary daily data, quality results, gap metadata, split code and M3 tests. It does not supply fitted models, metrics, comparative model conclusions, feature files or PPT. Final count, full protocol freeze, source gaps and actual identity/Git evidence are not fabricated.


## Interface constraints

Cosmetics metadata must be passed with cfg['m3']['sources']['cosmetics']['split']; primary metadata uses cfg['m3']['sources']['multi_store']['split']. Every metadata row contains dataset matching split.dataset. The splitter rejects missing or mismatched source identity. Prediction origins are last input days, not first target days. The primary first validation target day is 2019-11-01, following origin 2019-10-31.

A null candidate output_file means no published daily-contract input exists. Check readiness before downstream work or use read_candidate_daily, which raises a clear ValueError for unavailable data. Manifest audit metadata must not be read as a daily table. Preparation configuration retains m3.sources; an unrelated runtime-only configuration cannot supply omitted preparation settings.

The one-week primary validation span is insufficient for strong tuning conclusions, even with multiple categories. The 28-day primary training case has zero samples. The project lead must decide whether to obtain more history or authorize a restricted preliminary scope. No such decision is assumed here.
