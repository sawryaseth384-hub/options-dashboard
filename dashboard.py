import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(layout="wide")

# =========================
# STYLE
# =========================
st.markdown("""
<style>
body {background-color: #0A0F18; color: white;}
.block-container {padding-top: 1rem;}
div[data-testid="metric-container"] {
    background: #111827;
    border-radius: 10px;
    padding: 10px;
    border: 1px solid #1F2937;
}
</style>
""", unsafe_allow_html=True)

# =========================
# HEADER
# =========================
def render_header():
    st.markdown("""
    ### 📊 NIFTY ▲ | BANKNIFTY ▼ | SENSEX ▲ | DOW ▼ | GOLD ▲ | CRUDE ▼ | VIX  
    🟢 LIVE
    """)

# =========================
# DECISION BAR
# =========================
def render_decision(data):
    col = st.columns(6)

    col[0].metric("Spot", data["spot"])
    col[1].metric("PCR", round(data["pcr"], 2))
    col[2].metric("ATM", data["atm"])
    col[3].metric("Bias", data["bias"])
    col[4].metric("Signal", data["signal"])
    col[5].metric("Confidence", data["confidence"])

# =========================
# LEVELS
# =========================
def render_levels(data):
    col = st.columns(3)

    col[0].success(f"Support: {data['support']}")
    col[1].error(f"Resistance: {data['resistance']}")
    col[2].info(f"Max Pain: {data['max_pain']}")

# =========================
# OPTION CHAIN
# =========================
def render_table(df):
    st.subheader("📊 Option Chain")
    st.dataframe(df, use_container_width=True)

# =========================
# CHARTS
# =========================
def render_charts(df):
    col1, col2 = st.columns(2)

    with col1:
        fig = px.bar(df, x="Strike", y=["CE OI", "PE OI"])
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig2 = px.line(df, x="Strike", y=["CE LTP", "PE LTP"])
        st.plotly_chart(fig2, use_container_width=True)

# =========================
# STRIKE ANALYSIS
# =========================
def render_strike(df):
    st.subheader("🎯 Strike Analysis")

    strike = st.selectbox("Select Strike", df["Strike"])
    row = df[df["Strike"] == strike].iloc[0]

    col1, col2 = st.columns(2)

    with col1:
        st.write("CE Data")
        st.write(row[["CE OI", "CE LTP", "CE Delta"]])

    with col2:
        st.write("PE Data")
        st.write(row[["PE OI", "PE LTP", "PE Delta"]])

# =========================
# MAIN FUNCTION
# =========================
def run_dashboard(data, df):

    render_header()
    render_decision(data)
    render_levels(data)
    render_table(df)
    render_charts(df)
    render_strike(df)
