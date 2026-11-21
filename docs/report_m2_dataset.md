# Data: Sources, Scale, Aggregation Pipeline, and Limitations（M2 报告章节草稿）

> 交接说明：这是报告 **Data & Preprocessing** 章里由 M2 负责部分的英文草稿
> （读取与聚合；质量审核、类别选择、切分由 M3 撰写）。所有数字均为本机
> `scripts/run_m2_pipeline.sh` 正式运行实测，逐项核对见
> `reports/tables/aggregation_check.csv` 与 `reports/aggregation_check_report.md`。
> 按课程规则，团队须在此基础上独立改写后才能用于提交。

## Data Sources

We use two public clickstream datasets released within the same ecosystem (Rees46 Open CDP) on Kaggle, whose event schema is identical:

1. **Multi-category store (primary, development).** `mkechinov/ecommerce-behavior-data-from-multi-category-store`: user events from a large multi-category e-commerce site. The Kaggle release currently hosts **two monthly files** (2019-10, 2019-11) totalling **109,950,743 raw events** (104,335,509 views, 3,955,446 cart events, 1,659,788 purchase events; 42,448,764 events in October alone). The release description still advertises "7 months", but versions history and file listings show the 2019-12 … 2020-04 files were never published in this Kaggle dataset (see *Acquiring additional months* below).
2. **Cosmetics shop (external-validation candidate).** `mkechinov/ecommerce-events-history-in-cosmetics-shop`: **five monthly files** (2019-10 … 2020-02), **20,692,840 raw events** (9,657,821 views, 5,768,333 cart events, 1,287,007 purchase events). It is reserved as an out-of-sample store; it informs no development decision.

Two datasets from the task brief were not used, following the team's data-selection record (2026-11-05) and the project's prediction target:

- **Retailrocket** (`retailrocket/ecommerce-dataset`): 2,756,101 events over 4.5 months (2015); purchase events concentrate on few items (median 1 purchase per purchased item), and categories require an item–property join. The team explicitly deprioritised it for development.
- **E-commerce delivery & shipping 2026** (`datascikhan/e-commerce-delivery-and-shipping-data-2026`): an order-fulfilment/logistics table ("why do some orders arrive late"), not a behavioral event log; it has no view/cart/purchase event stream and cannot produce the category × date behavior series the project predicts.

Licensing and citation requirements are to be re-verified against the download pages before submission (assignment §3.8); Kaggle metadata for the primary dataset lists *"Data files © Original Authors"*. The processed tables we publish contain only aggregated counts.

## Scale and Unit of Analysis

Raw rows are *events*: one user performing one action on one product at one second. 110M events ≠ users ≠ orders ≠ units sold; we therefore aggregate. The analysis unit is **(UTC date, category) × {views, cart, purchase}**. After aggregation the primary table `daily_all_categories.csv` contains **36,555 rows covering 61 days × 691 categories**; the cosmetics table contains **63,546 rows covering 152 days × 525 categories**. Per-month details (counts, coverage, zero-purchase share) are in `reports/aggregation_check_report.md`.

## Aggregation Pipeline

`scripts/run_m2_pipeline.sh` → `scripts/build_daily.py` → `src/demandlens/data/loader.py` + `aggregate.py`:

1. **Chunked reading (D1).** `pandas.read_csv(..., usecols=[event_time, event_type, category_id, category_code], chunksize=10^6)`; the largest monthly file (**8.39 GiB**, 67.5M events) processes on a laptop without loading it into memory.
2. **Normalization.** `event_type` lower-cased; events outside the contract set {view, cart, purchase} (e.g. `remove_from_cart`, which the cosmetics shop emits 812k times per month) are counted but excluded; `event_time`'s fixed-width UTC prefix is strictly parsed (`YYYY-MM-DD`); rows with unparsable dates or non-integer `category_id` are counted and excluded (0 such rows in the months processed so far).
3. **Aggregation (D2).** Per-chunk `groupby(date, category_id, event_type).size()`, then sum across chunks. Rows are emitted only for observed (date, category) pairs — **no zero-filling, no category filtering** (the M2 contract file); M3 audits gaps, selects categories, and completes the calendar into `daily_category.csv`.
4. **Verification (D2 acceptance).** For every month and event type, aggregated counts must equal the raw counts that entered aggregation: **8/8 checks OK, 0 FAIL**. The check table also records exclusions, same-contract-columns rows (a suspected-duplicate signal), per-category `category_code` consistency (0 conflicts), and coverage. Our October aggregates independently reproduce the team's 2026-11-05 manual scan exactly (42,448,764 events; 742,849 purchases; top-10 categories = 68.7% of purchases; mean purchases per category-day 42.07).

Preliminary train/validation/test boundaries (time-ordered, non-overlapping 7-day evaluation blocks) are drafted in `docs/preliminary_split.md` + `reports/tables/preliminary_split.csv` for M3 to audit and freeze; the split uses calendar dates only and leaks no test-period information.

## Acquiring Additional Months (Phase 2, per assignment §3.3)

The assignment plans Phase 1 on 2019-10 + 2019-11 (done here) and Phase 2 on ≥ 4 months. Paths we verified on 2026-11-17:

- Kaggle mirror `mmmarchu/tabbccc` hosts all seven monthly CSVs but **requires Kaggle authentication** (anonymous API returns 403). Any team member with a Kaggle account can run `kagglehub.login()` once, then `scripts/build_daily.py --dataset multi_store --months 2019-Dec …` — the pipeline only needs the files reachable via `kagglehub` or placed under `data/raw/multi_store/`; **no code changes** (D5).
- HuggingFace mirrors of the later months exist but are gated/private as of this date.
- The vendor's own distribution (rees46.com open-data page) is the canonical source for the full 7-month release.
- Until then, the frozen Phase-1 table (61 days) still satisfies window construction (28-day lookback + 7-day horizon), but the preliminary val/test spans are small (see `docs/preliminary_split.md`, rule C) — extending months is the single most valuable data-side improvement, owned by the team in Phase 2.

## Limitations

- **Missing rows ≠ zero purchases.** Absent (date, category) pairs may be collection gaps; M3 must audit them before zero-filling windows. In 2019-10, 17,657 of 19,344 possible category-day pairs are observed (91.3%); November 18,898/20,520 (92.1%).
- **Duplicates.** We do not read `user_id`, so true duplicate detection is out of scope at this stage; the check table reports rows identical on the four contract columns as a *suspected*-duplicate signal only (e.g. 33% in 2019-11 — mostly distinct users viewing a popular product in the same second). Assignment §3.7's full-dedup caveat remains a stated limitation.
- **`category_code` sparsity.** The multi-category store emits a readable code for 92% of October events, but **372 of 624 categories (59.6%) never carry a code**; the cosmetics shop has essentially no usable codes (96.8% of events missing, 473/489 categories uncoded). Categories therefore stay as anonymous IDs; codes are auxiliary labels only.
- **Semantics.** Purchase *events* are a proxy for demand; they are not orders or units sold. Prices (with zero-price rows) and currency were not validated and are unused in this stage.
- **Single source, single period.** All months come from one store's 2019–2020 log; demand patterns may not transfer to other merchants — motivating the cosmetics external-validation candidate (whose December may exhibit holiday effects useful as a stress test).
