import streamlit as st
import plotly.graph_objects as go
from core.api import get_option_chain


def show_options(data):

    st.markdown("## ⚡ Option Chain Dashboard")

    df = get_option_chain()

    # 🔥 METRICS
    col1, col2, col3 = st.columns(3)

    col1.metric("Spot", "₹22450")
    col2.metric("PCR", "0.92")
    col3.metric("Max Pain", "22500")

    # 🔥 CHART
    fig = go.Figure()

    fig.add_bar(x=df["Strike"], y=df["Call OI"], name="Call OI")
    fig.add_bar(x=df["Strike"], y=df["Put OI"], name="Put OI")

    st.plotly_chart(fig, use_container_width=True)

    # 🔥 TABLE
    st.dataframe(df, use_container_width=True)

    # 🔥 AI SIGNAL
    st.markdown("### 🤖 AI Signal")

    st.success("🟢 BULLISH")
