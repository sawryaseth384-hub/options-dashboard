import streamlit as st
import pandas as pd
import time

# Dhan Modules
from dhan_data.instruments import get_symbol_data
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
st.title("🔬 Full Dhan Modules Scan (Stable Version)")

# =========================
# 1. TOKEN
# =========================
st.subheader("1. Token")
token = get_token()
st.write(f"Token: {'✅' if token else '❌'}")

# =========================
# 2. SYMBOL SETUP
# =========================
st.subheader("2. Symbol Resolution")

symbols = {
    "NIFTY": (13, "IDX_I"),
    "RELIANCE": (2885, "NSE_EQ"),
    "TCS": (11536, "NSE_EQ"),
    "HDFCBANK": (1333, "NSE_EQ"),
}

for sym, (sec, seg) in symbols.items():
    st.write(f"{sym}: sec_id={sec}, segment={seg}")

nifty_sec, nifty_seg = symbols["NIFTY"]

# =========================
# 3. EXPIRY LIST
# =========================
st.subheader("3. Expiry List (NIFTY)")
exp_list = get_expiry(nifty_sec, nifty_seg)

if exp_list:
    st.write(exp_list[:5])
else:
    st.warning("No expiry data")

# =========================
# 4. OPTION CHAIN
# =========================
st.subheader("4. Option Chain")

if exp_list:
    expiry = exp_list[0]
    oc_data = get_option_chain(nifty_sec, expiry, nifty_seg)

    if oc_data and "data" in oc_data:
        spot = oc_data["data"].get("last_price")
        oc = oc_data["data"].get("oc", {})
        strikes = sorted([int(float(s)) for s in oc.keys()])

        st.write(f"Spot: {spot}")
        st.write(f"Strikes Count: {len(strikes)}")
    else:
        st.error("Option Chain Failed")

# =========================
# 5. LTP (API BASED)
# =========================
st.subheader("5. Live LTP (Stable API)")

ltp = get_ltp(nifty_sec, nifty_seg)
st.write(f"LTP: {ltp}")

# =========================
# 6. HISTORICAL DATA
# =========================
st.subheader("6. Historical Data")

hist = get_historical(nifty_sec, nifty_seg)

if hist:
    st.write(f"Data Points: {len(hist)}")
else:
    st.warning("No historical data")

# =========================
# 7. CANDLESTICK
# =========================
st.subheader("7. Candlestick")

chart_sec = 26000
chart_seg = "NSE_IDX"

candle_df = get_candle_data(chart_sec, chart_seg)

if candle_df is not None:
    fig, trend = plot_candle(candle_df)
    st.write(f"Trend: {trend}")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("Candle data failed")

# =========================
# 8. AUTO REFRESH
# =========================
st.subheader("🔄 Auto Refresh")

if st.button("Refresh"):
    st.rerun()

st.success("✅ App Running Stable")
