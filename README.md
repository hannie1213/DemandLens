# DemandLens

**E-commerce category demand forecasting & merchant decision support.**

DemandLens turns raw e-commerce behavior logs into a next-day demand forecast. A merchant enters the last few days of daily views, add-to-carts, and purchases for a product category, and DemandLens returns tomorrow's expected purchase-event count, a prediction interval, and a comparison against simple heuristics — so operators can plan staffing, packing, and promotions around what is actually likely to sell.

## How it works

DemandLens is a time-series forecasting application built around a single, well-defined question: **how many purchase events will a category have tomorrow?**

| Item | Definition |
| --- | --- |
| Forecast unit | One product category on one UTC calendar day |
| Input | Historical daily views, add-to-cart, and purchase counts up to the end of day `t`, plus calendar features |
| Target | Purchase-event count for the same category on day `t+1` |
| Forecast time | After day `t` is complete, predict `t+1` |
| Optional extension | 7-day total purchase count |

> A *purchase event* is one `purchase` row in the event log — it is **not** an order and **not** units sold. This distinction is shown in the app and should be kept in mind when comparing forecasts.

## Features

- **Next-day forecast** with a prediction interval.
- **Baseline comparison** — every forecast is shown against persistence ("tomorrow = today") and a 7-day moving average, so it is clear when the model adds value.
- **History replay** — pick a category and a past date, forecast, then reveal the true value.
- **Model diagnostics** — per-category error, ablation results, and feature-importance views.
- **CSV input** — paste or upload the last 7 days of views / add-to-carts / purchases.

## Methods

- **Baselines:** persistence (`tomorrow = today`), same weekday last week, and 7-day moving average.
- **Models:** KNN regression, Decision Tree regression, and Random Forest regression — interpretable classical models, chosen over deep learning for transparency and training cost.
- **Evaluation:** strictly chronological train/validation/test split with rolling origins; MAE, RMSE, and WAPE; improvement over baseline; prediction intervals from empirical quantiles of validation residuals.

## Repository structure

```
demandlens/
├── README.md               # this file
├── README.txt              # quick-start instructions
├── requirements.txt        # Python dependencies
├── data/
│   ├── raw/                # raw datasets (not committed; see README inside)
│   └── processed/          # daily-aggregated tables
├── notebooks/              # 01_inspect ... 07_external
├── src/                    # data.py, features.py, models.py, evaluate.py
├── models/                 # trained joblib artifacts (local; gitignored)
├── app/                    # Streamlit app: Home.py + pages/
├── reports/                # experiment logs and figures
└── docs/
    └── evaluation_protocol.md
```

## Getting started

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app/Home.py
```

The app runs locally by default and does not require a network connection at runtime.

## Data

Raw data is large and **not committed** to the repository. See [`data/raw/README.md`](data/raw/README.md) for the source datasets, download links, and licensing notes.

## Limitations

- Trained on historical e-commerce data (2019–2020); this is a method demonstration and must be retrained and validated on a merchant's own data before production use.
- Forecasts purchase-event counts, not revenue, orders, units, or replenishment quantities.
- Only a few months of history are used, so annual seasonality and long-term trends are not captured.

## License

[MIT](LICENSE)
