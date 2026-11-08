# models — Trained model artifacts

Stored locally as joblib files; large binaries are gitignored.

## Naming convention (to be finalized)

`<model>_<target_scale>_<featureset>_<date>.joblib`

## Version record

Keep a short entry per model: date, git commit, dataset range, features, hyperparameters, and metrics.

## Constraints

- Random seed is fixed project-wide.
- Keep each model file small (limit tree count/depth for Random Forest).
- `predict()` interface: see `src/models.py`.
