# data/processed — Daily aggregated tables

Small, committed tables produced from `data/raw` by `notebooks/02_build_daily.ipynb`.

## Schema (agreed daily table)

| Column | Type | Description |
| --- | --- | --- |
| `date` | date | UTC calendar day |
| `category_id` | int | Category identifier from the source data |
| `category_name` | str | Most frequent `category_code` for that `category_id` |
| `views` | int | Number of `view` events |
| `cart` | int | Number of `cart` events |
| `purchase` | int | Number of `purchase` events (the forecast target) |

Notes:

- One row = one `category_id` on one `date`.
- Missing calendar days are filled with zeros only after confirming the site was collecting normally that day.
- Aggregated totals must match the raw event counts exactly (consistency check).
