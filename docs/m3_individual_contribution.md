# Individual contribution to data quality and time splitting

Name and student ID: [TO BE COMPLETED]. Actual Git branch and commit references: [TO BE COMPLETED].

## Scope and inputs

My contribution covers the quality review of aggregated daily tables, category selection using development data, calendar completeness and chronological split rules. The inputs are the supplied primary-store and cosmetics daily tables, with 36,555 and 63,546 rows. Raw-file acquisition and aggregation are described separately. I do not claim model training, feature development, model evaluation or application implementation in this contribution.

## Quality review

The implementation checks required fields, valid dates, exact category identifiers, nonnegative integer counts and unique date-category keys. It also records missing names, name-to-ID relationships, path depths, absent category-days, observed zero-purchase proportions and unusual peaks. Peaks are marked for review rather than deleted. Integer-valued monthly text is normalized in memory without changing source observations. Supporting monthly totals are checked against supplied counters; this is not an independent raw-file rescan. Unknown dates remain distinct from observed zero counts.

## Category selection and calendar preparation

Both 10-category and 20-category candidates are retained for later model comparison. Selection uses October 2019 for primary data and October–November 2019 for cosmetics. Implemented eligibility checks consider observed history, purchase activity and conflicting category names. Anonymous IDs are retained. Activity strata include high, middle and low purchase-volume groups, so selection does not consist solely of the most popular categories. The thresholds and quotas are explicit implementation choices, not proven optimal settings.

The primary candidates produce 610 and 1,220 fully observed daily rows. Cosmetics candidates contain 71 identical unknown category-days, so complete integer-contract daily exports are withheld. A shared gap list records the precise dates. Candidate-specific readiness and date feasibility are saved in the run manifest. No missing count is invented and no category is replaced because of later missingness.

## Time splitting and verification

The split function assigns samples using source-specific prediction origins and strict target-end boundaries. It rejects incorrect source identity, excludes unknown input and target days and retains fixed weekly evaluation grids. The metadata audit compares 7-, 14- and 28-day histories without generating features or training models. The primary 28-day case has no training samples. Its single validation week limits tuning conclusions.

The handoff includes source code, four category selection tables, two primary daily tables, the quality report, configuration, protocol, notebook outputs and a detailed experiment log. Thirty-seven task checks pass, including explicit source mismatch and unavailable-export checks. Three notebook code cells were executed. Configuration assumptions and remaining source-data decisions are documented for the project handoff.

## Limitations and personal evidence

Raw-event duplicate sampling and source completeness were not independently established. Cosmetics gaps and insufficient primary history remain open. The confirmed comparison arrangement does not imply a frozen final category count or successful model results. Project integration is a separate responsibility. Personal Git references and identity must be supplied from actual records. This appendix describes the implemented contribution; it does not fabricate commits, reviews or unperformed experiments.
