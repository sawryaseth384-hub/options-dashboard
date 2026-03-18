import streamlit as st
import pandas as pd

from core.api import get_option_chain


def show_options(data):

    st.markdown("## ⚡ Options Dashboard")

    # 🔥 DATA
    option_data = get_option_chain()
    df = pd.DataFrame(option_data)

    # 🔥 METRICS
    col1, col2, col3 = st.columns(3)

    col1.metric("Spot", "23700")
    col2.metric("PCR", "0.92")
    col3.metric("Trend", "Bullish")

    st.divider()

    # 🔥 TABLE
    st.dataframe(df, use_container_width=True)

    st.success("🟢 Market looks bullish")
