# data/raw — Raw datasets

This directory holds the raw source data. **Raw files are not committed to Git** (they are too large — the Multi-category Store dataset is several GiB).

## Primary dataset — Multi-category Store (REES46)
- Kaggle: https://www.kaggle.com/datasets/mkechinov/ecommerce-behavior-data-from-multi-category-store
- Fields: `event_time`, `event_type`, `product_id`, `category_id`, `category_code`, `brand`, `price`, `user_id`, `user_session`.
- Stated range: 2019-10 to 2020-04.

Download the CSV(s) and place them here (e.g. `data/raw/2019-Oct.csv`). Then run `notebooks/01_inspect.ipynb` and `notebooks/02_build_daily.ipynb`.

## External validation — Cosmetics Shop
- Kaggle: https://www.kaggle.com/datasets/mkechinov/ecommerce-events-history-in-cosmetics-shop

## Supplementary — M5 Forecasting
- Kaggle: https://www.kaggle.com/competitions/m5-forecasting-accuracy

> Verify each dataset's license and citation requirements on its download page before use.
