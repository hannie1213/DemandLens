"""DemandLens — Streamlit multi-page app (entry point).

Owner: M1

Run locally:
    streamlit run app/Home.py

Pages are auto-discovered from app/pages/.
"""

import streamlit as st

st.set_page_config(page_title="DemandLens", page_icon="📈", layout="wide")

st.title("DemandLens")
st.caption("E-commerce category demand forecasting & merchant decision support")

st.markdown(
    """
    DemandLens predicts tomorrow's **purchase-event count** for a product category,
    given the last few days of views, add-to-cart, and purchases.

    > Placeholder home page. Content (project intro, usage steps, data-source and
    > limitation statement).
    """
)

st.info(
    "Use the sidebar to open a page: Data Exploration, Forecast, History Replay, "
    "Model Performance, About."
)
