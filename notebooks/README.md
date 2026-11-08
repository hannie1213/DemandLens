# notebooks — Experiments and analysis

Run in order. Each notebook focuses on one stage of the pipeline.

| Notebook | Purpose |
| --- | --- |
| `01_inspect` | Inspect raw event log: schema, row counts, quality checks |
| `02_build_daily` | Chunked read → daily aggregation (date × category × event_type) → quality checks → category selection → calendar fill |
| `03_eda` | EDA: category size, daily trends, weekday effects, missingness |
| `04_features` | Feature engineering + leakage audit |
| `05_models` | Baselines, KNN / Decision Tree / Random Forest, rolling validation, tuning (E1, E4) |
| `06_experiments` | Ablation (E2), scale experiments (E3, E6), error analysis (E5), prediction intervals, interpretation |
| `07_external` | Cosmetics external validation (E7) and M5 supplementary validation (E8) |
