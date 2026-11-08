DemandLens — E-commerce category demand forecasting
=======================================================================

1. What this project does
   Predicts tomorrow's purchase-event count for a product category, given the
   last few days of daily views, add-to-cart, and purchase counts. It provides a
   forecast, a prediction interval, and a comparison against naive baselines.

2. Requirements
   Python 3.11+ (recommended). Install dependencies:

       pip install -r requirements.txt

3. How to run the website

       streamlit run app/Home.py

4. How the project works (overview)
   - data/raw:       raw event logs (download links in data/raw/README.md; NOT included)
   - notebooks/:     inspect -> build daily table -> EDA -> features -> models ->
                     experiments -> external validation
   - src/:           data.py, features.py, models.py, evaluate.py
   - app/:           Streamlit pages (Forecast, History Replay, Model Performance, ...)
   - models/:        trained joblib files (loaded by the app, never trained at runtime)

5. Data
   See data/raw/README.md for dataset links and licenses.

6. License
   MIT — see LICENSE.
