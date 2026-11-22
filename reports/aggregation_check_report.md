# Aggregation Check Report (M2 deliverable)

Generated at: 2026-11-17T19:51:42

The data contract is in assignment 3.6; item-by-item figures are in `reports/tables/aggregation_check.csv`. This report only interprets the numbers; quality audit, category selection, and calendar completion are M3's responsibility.

## Conclusions

- Consistency checks **28 OK / 0 FAIL**; every event-type total is identical before and after aggregation (requirement D2 acceptance passed).

## Dataset Overview

- **multi_store**: 2 months (2019-Oct .. 2019-Nov), 109,950,743 raw events (109,950,743 entered aggregation; 0 out-of-contract), raw files 13.67 GiB total
- **cosmetics**: 5 months (2019-Oct .. 2020-Feb), 20,692,840 raw events (16,713,161 entered aggregation; 3,979,679 out-of-contract), raw files 2.27 GiB total

## Per-Month Details

| Dataset | Month | view | cart | purchase | Categories | Days | Zero-purchase row share |
|---|---|---:|---:|---:|---:|---:|---:|
| multi_store | 2019-Oct | 40,779,399 | 926,516 | 742,849 | 624 | 31 | 31.7% |
| multi_store | 2019-Nov | 63,556,110 | 3,028,930 | 916,939 | 684 | 30 | 34.9% |
| cosmetics | 2019-Oct | 1,862,164 | 1,232,385 | 245,624 | 489 | 31 | 25.5% |
| cosmetics | 2019-Nov | 2,076,132 | 1,311,807 | 322,417 | 491 | 30 | 23.2% |
| cosmetics | 2019-Dec | 1,728,331 | 927,124 | 213,176 | 481 | 31 | 25.4% |
| cosmetics | 2020-Jan | 2,037,608 | 1,148,323 | 263,797 | 481 | 31 | 24.0% |
| cosmetics | 2020-Feb | 1,953,586 | 1,148,694 | 241,993 | 487 | 29 | 23.6% |

## Quality Reference Figures (for M3's audit; does not replace the quality report)

- **multi_store**: invalid-date rows 0; invalid-category rows 0; out-of-contract events 0; estimated rows identical on the four contract columns 33,333,787; category-code conflicts (within-month 0 / cross-month 0)
- **cosmetics**: invalid-date rows 0; invalid-category rows 0; out-of-contract events 3,979,679; estimated rows identical on the four contract columns 1,982,004; category-code conflicts (within-month 0 / cross-month 0)

## Limitations (consistent with assignment 3.7)

- "Rows identical on the four contract columns" is a suspected-duplicate signal (user_id is not read, so normal events on the same product within the same second are also counted), not true duplicates; cross-chunk duplicates are not covered, and full deduplication is costly — recorded as a limitation.
- The zero-purchase row share is computed over "rows that have a record"; (category, date) pairs with no record are not in the table and must not be treated as zero purchases — M3 must judge whether they are collection gaps.
- The cosmetics shop has a very high category_code missing rate; readable category names serve only as auxiliary labels.
- Event count ≠ order count ≠ units sold; the purchase event is a proxy for demand.
