# DemandLens Data Dictionary (owned by M2)

Applies to: raw event log → daily aggregated table `daily_all_categories.csv` (contract 3.6).
Primary dataset: Multi-category Store (large multi-category e-commerce, released by Rees46); external-validation candidate: Cosmetics Shop.
Both datasets share the same field structure and processing rules.

## 1. Raw Event CSV (one file per month, not stored in the repo)

| Column | Type | Meaning | M2 handling |
|---|---|---|---|
| event_time | text, `YYYY-MM-DD HH:MM:SS UTC` | Event time (UTC) | Take the first 10 characters as the date; count then exclude invalid values |
| event_type | text | view / cart / purchase (some months also have remove_from_cart) | Lowercase-normalize; only the three contract types enter aggregation, the rest are counted separately |
| product_id | integer | Product ID | Not read (not used in v1, see assignment 3.1) |
| category_id | integer | Category ID, one of the aggregation keys | Must parse to an integer, otherwise count and exclude |
| category_code | text, nullable | Category path (e.g. `computers.notebook`), sometimes missing | Record the set of codes seen per category; flag on conflicts |
| brand | text, nullable | Brand, sometimes missing | Not read |
| price | float | Price in the event record (currency unconfirmed, includes zero prices) | Not read |
| user_id | integer | User ID; event count ≠ unique users | Not read |
| user_session | text | Session ID; not the same concept as orders | Not read |

Reading method (requirement D1): `pandas.read_csv(..., usecols=[...4 columns...], chunksize=1_000_000)`
Chunked streaming processing; a single monthly file (largest ~9 GiB) completes on an ordinary laptop.

## 2. Daily Aggregated Table `daily_all_categories.csv` (contract 3.6)

One row per (date, category_id) combination; **no zero-filling, no category filtering** (M2's product).
M3 audits quality, selects categories, and completes the calendar to produce `daily_category.csv`; downstream uses only the latter.

| Column | Type | Description |
|---|---|---|
| date | date (UTC) | The UTC day the event falls on, ISO format `YYYY-MM-DD` |
| category_id | integer (int64) | Category ID |
| category_code | text, nullable | The category path seen for this category; on cross-chunk/cross-month inconsistency, join all values with `\|` and flag in the check table |
| views | integer ≥ 0 | Number of view events for this category on that day |
| cart | integer ≥ 0 | Number of cart events for this category on that day (excludes remove_from_cart) |
| purchase | integer ≥ 0 | Number of purchase events for this category on that day; **this is the only source of the prediction label** |

Semantic boundaries (must travel with the data):
- Event count ≠ order count ≠ units sold; the purchase event is the proxy label for "purchase activity over the next 7 days".
- Missing rows ≠ zero purchases: a (category, date) pair with no record may be a collection gap; M3 decides after auditing whether to zero-fill or exclude.
- remove_from_cart is not a contract event and does not affect the cart column.

## 3. Aggregation Check Table `reports/tables/aggregation_check.csv`

Columns: `dataset, month, check, raw_value, aggregated_value, diff, status`.
Key checks (status=OK/FAIL, others are INFO):

| check | Meaning |
|---|---|
| count:view / count:cart / count:purchase | Valid in-contract event count that entered aggregation == sum of the daily-aggregated column (D2 acceptance) |
| count_raw_all:{event} | Total rows of that event type in the raw file (including invalid rows; informational) |
| aggregatable_rows | Rows that entered aggregation == sum of the three daily-aggregated columns |
| excluded:other_event_types | Rows of out-of-contract events (e.g. remove_from_cart) |
| invalid:date_rows / invalid:category_rows | Rows with invalid date / invalid category ID |
| duplicate:same_contract_cols_est | Estimated number of rows identical on the four contract columns (event_time/event_type/category_id/category_code). **Note**: user_id is not read, so multiple normal views of a popular product within the same second also count; do not treat as true duplicates; cross-chunk duplicates are not covered |
| coverage:categories / coverage:dates | Number of categories / dates covered in the month |
| consistency:category_code_conflicts | Number of categories where one category_id maps to multiple category_code values |
| cross_month:category_code_conflicts | Number of categories with inconsistent codes across months (at the merged-table level) |
| file:size_bytes | Raw file size in bytes |

## 4. Cosmetics Shop Daily Table `daily_all_categories_cosmetics.csv`

Columns and semantics are identical to section 2; used for (candidate) external validation and does not participate in development-period tuning.
Note its category_code missing rate is very high (about 96.8% of October events have no code; 473/489 categories have no code at all —
use the figures measured in the check table), so readable category names are basically unusable; anonymous IDs are primary.

## 5. Preliminary Time Split `reports/tables/preliminary_split.csv`

Columns: `date, split, eval_block_start`.
- split ∈ {train, val, test}: all categories on the same UTC day are in the same partition (assignment 4.6).
- eval_block_start: the start day of a non-overlapping 7-day evaluation block (only val/test dates have a value),
  used to avoid highly correlated evaluation from consecutive sliding windows; a trailing interval shorter than 7 days does not participate in evaluation.
- This file is M2's draft; the final boundaries are written to `config/config.yaml` and frozen after M3's audit.
