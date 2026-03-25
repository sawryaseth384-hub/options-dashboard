import streamlit as st

from dhan_data.market_quote import get_ltp
from dhan_data.historical_data import get_historical
from dhan_data.chart import get_candle_data, plot_candle
from core.token_manager import get_token

st.set_page_config(layout="wide")
st.title("🚀 Dhan Trading Dashboard (Final)")

# =========================
# TOKEN
# =========================
st.subheader("1. Token")
token = get_token()
st.write(f"Token: {'✅' if token else '❌'}")

# =========================
# MARKET QUOTE
# =========================
st.subheader("2. Market Quote")

ltp = get_ltp(2885, "NSE_EQ")
st.write(f"RELIANCE LTP: {ltp}")

# =========================
# HISTORICAL
# =========================
st.subheader("3. Historical Data")

hist = get_historical(2885, "NSE_EQ")

if hist:
    st.write("Historical Loaded")
else:
    st.warning("No historical data")

# =========================
# CANDLE
# =========================
st.subheader("4. Candlestick")

df = get_candle_data(2885, "NSE_EQ")

if df is not None and len(df) > 0:
    fig, trend = plot_candle(df)
    st.write(f"Trend: {trend}")
    st.plotly_chart(fig)
else:
    st.warning("No candle data")

# =========================
# REFRESH
# =========================
if st.button("Refresh"):
    st.cache_data.clear()
    st.rerun()

st.success("✅ FINAL SYSTEM RUNNING")
