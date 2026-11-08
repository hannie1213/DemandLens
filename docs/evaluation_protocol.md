# Evaluation protocol (freeze before experiments)

> TODO: finalize and freeze before experiments start. Do not change after tests are run.

- **Splitting:** strictly chronological (train → validation → test); all categories of the same day go into the same split.
- **Rolling origin:** expanding window, one origin per week; report per-origin error spread, not just one test score.
- **Metrics:** MAE, RMSE, WAPE; improvement over baselines B0 and B2; per-category error table.
- **Prediction intervals:** empirical quantiles of validation residuals grouped by category size; report test-period coverage.
- **Selected categories:** number of categories N (10–30) and test-period dates to be fixed here.
- **Data note:** October data is EDA/development data, never test.

> Keep this file frozen once experiments start; never change it based on test results.
