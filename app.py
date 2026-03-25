import streamlit as st
import pandas as pd

# Dhan Modules
from dhan_data.expiry import get_expiry
from dhan_data.option_chain import get_option_chain
from dhan_data.market_quote import get_ltp
from dhan_data.historical_data import get_historical
from dhan_data.chart import get_candle_data, plot_candle

from core.token_manager import get_token

# =========================
# PAGE SETUP
# =========================
st.set_page_config(layout="wide")
st.title("🚀 Dhan Trading Dashboard (Stable)")

# =========================
# 1. TOKEN
# =========================
st.subheader("1. Token")
token = get_token()
st.write(f"Token: {'✅' if token else '❌'}")

# =========================
# 2. SYMBOLS
# =========================
st.subheader("2. Symbols")

symbols = {
    "NIFTY": (13, "IDX_I"),
    "RELIANCE": (2885, "NSE_EQ"),
}

for sym, (sec, seg) in symbols.items():
    st.write(f"{sym}: {sec}, {seg}")

nifty_sec, nifty_seg = symbols["NIFTY"]

# =========================
# 3. OPTION CHAIN
# =========================
st.subheader("3. Option Chain")

exp_list = get_expiry(nifty_sec, nifty_seg)

if exp_list:
    expiry = exp_list[0]
    oc_data = get_option_chain(nifty_sec, expiry, nifty_seg)

    if oc_data and "data" in oc_data:
        spot = oc_data["data"].get("last_price")
        st.write(f"Spot: {spot}")
    else:
        st.error("Option Chain Failed")

# =========================
# 4. MARKET QUOTE
# =========================
st.subheader("4. Market Quote")

ltp = get_ltp(2885, "NSE_EQ")
st.write(f"RELIANCE LTP: {ltp}")

# =========================
# 5. HISTORICAL DATA
# =========================
st.subheader("5. Historical Data")

hist = get_historical(2885, "NSE_EQ")

if hist:
    st.write(f"Data Points: {len(hist)}")
else:
    st.warning("No historical data")

# =========================
# 6. CANDLESTICK
# =========================
st.subheader("6. Candlestick")

chart_sec = 2885
chart_seg = "NSE_EQ"

candle_df = get_candle_data(chart_sec, chart_seg)

if candle_df is not None and len(candle_df) > 0:
    fig, trend = plot_candle(candle_df)
    st.write(f"Trend: {trend}")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("No candle data")

# =========================
# 7. REFRESH
# =========================
st.subheader("🔄 Refresh")

if st.button("Refresh"):
    st.cache_data.clear()
    st.rerun()

st.success("✅ Dashboard Running Stable")
