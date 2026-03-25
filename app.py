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

# WebSocket
from dhan_data.live_market_feed import (
    start_live_feed,
    subscribe_instrument,
    get_live_ltp
)

from dhan_data.depth_feed import (
    start_depth_feed,
    subscribe_depth,
    get_depth,
    subscribe_ltp,   # optional, if you want LTP from depth feed
    get_ltp          # optional
)

from core.token_manager import get_token

# =========================
# PAGE SETUP
# =========================
st.set_page_config(layout="wide")
st.title("🔬 Full Dhan Modules Scan")

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

# Symbol info for different purposes
symbols = {
    "NIFTY": (13, "IDX_I"),
    "RELIANCE_FNO": (2885, "NSE_FNO"),
    "TCS": (11536, "NSE_FNO"),
    "HDFCBANK": (1333, "NSE_FNO"),
}

# Separate mapping for depth (equity only)
depth_symbols = {
    "RELIANCE_EQ": (2885, "NSE_EQ"),   # equity cash
}

for sym, (sec, seg) in symbols.items():
    st.write(f"{sym}: sec_id={sec}, segment={seg}")

nifty_sec, nifty_seg = symbols["NIFTY"]
rel_fno_sec, rel_fno_seg = symbols["RELIANCE_FNO"]
rel_eq_sec, rel_eq_seg = depth_symbols["RELIANCE_EQ"]

# =========================
# 3. EXPIRY LIST (NIFTY)
# =========================
st.subheader("3. Expiry List (NIFTY)")
exp_list = get_expiry(nifty_sec, nifty_seg)
if exp_list:
    st.write(f"First 5 Expiries: {exp_list[:5]}")
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
        st.write(f"Strikes: {len(strikes)}")
    else:
        st.error("Option Chain Failed")

# =========================
# 5. LIVE LTP (INDEX)
# =========================
st.subheader("5. Live LTP (WebSocket)")
if "ltp_started" not in st.session_state:
    start_live_feed()
    subscribe_instrument(nifty_sec, nifty_seg)
    st.session_state.ltp_started = True
time.sleep(2)
ltp = get_live_ltp()
st.write(f"LTP: {ltp}")

# =========================
# 6. DEPTH FEED (STOCK ONLY – EQUITY CASH)
# =========================
st.subheader("6. Depth Feed (RELIANCE – Equity)")
if "depth_started" not in st.session_state:
    start_depth_feed()
    time.sleep(1)
    subscribe_depth(rel_eq_sec, rel_eq_seg)   # use equity segment
    st.session_state.depth_started = True
time.sleep(2)
depth = get_depth()
if depth["bids"] or depth["asks"]:
    st.success("✅ Depth Data Received")
    col1, col2 = st.columns(2)
    with col1:
        st.write("📉 Bids")
        st.dataframe(pd.DataFrame(depth["bids"][:5]))
    with col2:
        st.write("📈 Asks")
        st.dataframe(pd.DataFrame(depth["asks"][:5]))
else:
    st.warning("❌ No depth data yet")

# =========================
# 7. HISTORICAL DATA
# =========================
st.subheader("7. Historical Data")
hist = get_historical(nifty_sec, nifty_seg)
if hist:
    st.write(f"Data Points: {len(hist)}")
else:
    st.warning("No historical data")

# =========================
# 8. CANDLESTICK (FIXED)
# =========================
st.subheader("8. Candlestick")
chart_sec = 26000
chart_seg = "NSE_IDX"
candle_df = get_candle_data(chart_sec, chart_seg)
if candle_df is not None:
    fig, trend = plot_candle(candle_df)
    st.write(f"Trend: {trend}")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("❌ Candle data failed")

# =========================
# 9. STATIC LTP
# =========================
st.subheader("9. Market Quote")
ltp_static = get_ltp(nifty_sec, nifty_seg)
st.write(f"Static LTP: {ltp_static}")

st.success("✅ Scan Complete")
