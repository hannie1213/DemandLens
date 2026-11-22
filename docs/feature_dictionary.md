# Feature Dictionary — M4 Feature Engineering

> Records, item by item, the name, meaning, formula, and date range of every feature produced by `build_features`, as the basis for leakage auditing (paired with `tests/test_windows_leakage.py`).

## 0. Notation and Conventions

- **Prediction origin t**: `input_end_date` (the last day of the input window).
- **Input window**: `[t - (L - 1), t]`, L = `task.lookback_days` (7 / 14 / 28).
- **Target window**: `[t + 1, t + H]`, H = `task.horizon_days` (fixed 7).
- **Target y**: the total `purchase` events of this category over the target window (one scalar): `y = Σ_{d=t+1}^{t+H} purchase_d`.
- **Strict time isolation**: every event-statistic feature sums only over the input window "up to and including the prediction origin", and is always clipped to `[input_start_date, input_end_date]`; it never reads the target period or any future day. Calendar features use only the target week's "known calendar information" (weekday / month / cross-month / public holidays) and read no future event data.
- **Short-window safety**: when `L = 7` there is no complete "previous 7 days" (`[t-13, t-7]` is entirely before `input_start`), so all `*_prev7_total` are 0 (a true "no previous-7-day count"); the derived `*_trend` and `purchase_wow_ratio` take neutral values under the "denominator-zero fallback" below and **do not degrade into the raw total**.
- **Denominator-zero fallback**: if the denominator of a ratio/trend feature is 0, fall back to a neutral value (avoids division-by-zero, `inf`, and scale-distorting raw values) —
  - trend features (`purchase_trend` / `views_trend` / `cart_trend`) → `0.0` (meaning "no change");
  - week-over-week (`purchase_wow_ratio`) → `1.0` (meaning "flat vs last week");
  - conversion ratios (`cart_view_ratio` / `purchase_cart_ratio`) → `0.0` (meaning "no conversion").
  All of the above are "event-count ratios", not unique-user conversion rates.

## 1. Purchase Features (always generated)

| Feature | Meaning | Formula | Date range used |
| --- | --- | --- | --- |
| `purchase_last7_total` | Total purchases over the last 7 days | Σ purchase | `[t-6, t]` (clipped to the input window) |
| `purchase_prev7_total` | Total purchases over the previous 7 days | Σ purchase | `[t-13, t-7]` (clipped to the input window; 0 when L=7) |
| `purchase_last14_total` | Total purchases over the last 14 days | Σ purchase | `[t-13, t]` (clipped to the input window) |
| `purchase_last7_avg` | Daily average purchases over the last 7 days | last7_total / 7 | `[t-6, t]` |
| `purchase_trend` | Recent purchase trend (week-over-week change rate) | (last7_total − prev7_total) / prev7_total; 0.0 when prev7_total=0 | uses `[t-13, t]` |

## 2. Views & Cart Features (generated when `use_behavior=True`)

| Feature | Meaning | Formula | Date range used |
| --- | --- | --- | --- |
| `views_last7_total` | Total views over the last 7 days | Σ views | `[t-6, t]` |
| `views_prev7_total` | Total views over the previous 7 days | Σ views | `[t-13, t-7]` (0 when L=7) |
| `views_trend` | Views trend | (views_last7 − views_prev7) / views_prev7; 0.0 when views_prev7=0 | `[t-13, t]` |
| `cart_last7_total` | Total cart-adds over the last 7 days | Σ cart | `[t-6, t]` |
| `cart_prev7_total` | Total cart-adds over the previous 7 days | Σ cart | `[t-13, t-7]` (0 when L=7) |
| `cart_trend` | Cart-adds trend | (cart_last7 − cart_prev7) / cart_prev7; 0.0 when cart_prev7=0 | `[t-13, t]` |

## 3. Ratio Features (generated when `use_behavior=True`)

| Feature | Meaning | Formula | Date range used |
| --- | --- | --- | --- |
| `cart_view_ratio` | Cart / views (event-count ratio) | cart_last7 / views_last7; 0.0 when views_last7=0 | `[t-6, t]` |
| `purchase_cart_ratio` | Purchase / cart (event-count ratio) | purchase_last7 / cart_last7; 0.0 when cart_last7=0 | `[t-6, t]` |
| `purchase_wow_ratio` | Last-week purchases / previous-week purchases | purchase_last7 / purchase_prev7; 1.0 when purchase_prev7=0 | `[t-13, t]` |

## 4. Calendar Features (always generated; use only the target week's calendar info)

| Feature | Meaning | Formula | Date range used |
| --- | --- | --- | --- |
| `cal_target_weekday` | Weekday of the target week's start | target_start.weekday() (0=Mon … 6=Sun) | target week `[t+1, t+H]` (calendar only, no event data) |
| `cal_target_month` | Month of the target week's start | target_start.month (1–12) | target week (calendar only) |
| `cal_target_cross_month` | Whether the target week crosses a month boundary | 1 if target_start.month ≠ target_end.month else 0 | target week (calendar only) |
| `cal_target_holiday` | Whether the target week contains a public holiday | 1 if any day of the target week ∈ holidays else 0 | target week (public calendar only, no promo records) |

## 5. Category-Identity Features (generated when `use_category=True`)

| Feature | Meaning | Formula | Date range used |
| --- | --- | --- | --- |
| `cat_is_<id>` | Category One-Hot encoding | 1 if category_id == id else 0 | none (category identity, no time involved) |

- One column per `config['category_ids']` entry (i.e. M3's development-period `variants['10'].selected_ids`), ordered by integer id ascending.
- The encoding mapping is fit only on the development-period category list, **never on test-period data**.

## 6. Ablation Switches (for M6's E2 / E3)

| Switch | Effect | Kept when `False` | Added when `True` |
| --- | --- | --- | --- |
| `use_behavior` (E2) | views & cart | only sections 1, 4 (purchase + calendar) | sections 2, 3 (views / cart / ratios) |
| `use_category` (E3) | category identity | no category columns | section 5 (`cat_is_<id>` One-Hot) |

- M4 only provides the switches and feature output; running and analyzing the ablation experiments belongs to M6.

## 7. Output Column Order

`WINDOW_META_FIELDS` (sample_id, category_id, input_start_date, input_end_date, target_start_date, target_end_date) → feature columns (in the order of sections 1 → 2 → 3 → 4 → 5) → `y`.
