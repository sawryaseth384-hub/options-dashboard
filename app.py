import streamlit as st
import pandas as pd

# Modules
from dhan_data.market_quote import get_ltp
from dhan_data.historical_data import get_historical
from dhan_data.chart import get_candle_data, plot_candle
from dhan_data.expiry import get_expiry
from dhan_data.option_chain import get_option_chain
from core.token_manager import get_token, get_headers

# =========================
# PAGE SETUP
# =========================
st.set_page_config(layout="wide")
st.title("🚀 Dhan Trading Dashboard + Debug")

# =========================
# SIDEBAR DEBUG PANEL
# =========================
st.sidebar.title("🔧 Debug Panel")

debug_mode = st.sidebar.toggle("Enable Debug Mode")

# =========================
# 1. TOKEN
# =========================
st.subheader("1. Token")

try:
    token = get_token()
    headers = get_headers()
    st.success("✅ Token OK")

    if debug_mode:
        st.sidebar.write("Headers:", headers)

except Exception as e:
    st.error(f"❌ Token Error: {e}")

# =========================
# 2. MARKET QUOTE
# =========================
st.subheader("2. Market Quote")

try:
    ltp = get_ltp(2885, "NSE_EQ")
    st.write(f"RELIANCE LTP: {ltp}")

    if debug_mode:
        st.sidebar.success("LTP OK")

except Exception as e:
    st.error(f"❌ LTP Error: {e}")

# =========================
# 3. HISTORICAL
# =========================
st.subheader("3. Historical Data")

try:
    hist = get_historical(2885, "NSE_EQ")

    if hist:
        st.success("✅ Historical Loaded")

        if debug_mode:
            st.sidebar.write("Historical RAW:", hist)

    else:
        st.warning("⚠️ No historical data")

except Exception as e:
    st.error(f"❌ Historical Error: {e}")

# =========================
# 4. CANDLE
# =========================
st.subheader("4. Candlestick")

try:
    df = get_candle_data(2885, "NSE_EQ")

    if df is not None and len(df) > 0:
        fig, trend = plot_candle(df)
        st.write(f"Trend: {trend}")
        st.plotly_chart(fig)

        if debug_mode:
            st.sidebar.write("Candle DF:", df.head())

    else:
        st.warning("⚠️ No candle data")

except Exception as e:
    st.error(f"❌ Candle Error: {e}")

# =========================
# 5. OPTION CHAIN
# =========================
st.subheader("5. Option Chain")

try:
    exp_list = get_expiry(13, "IDX_I")

    if exp_list:
        expiry = exp_list[0]
        oc = get_option_chain(13, expiry, "IDX_I")

        if oc:
            st.success("✅ Option Chain Loaded")

            if debug_mode:
                st.sidebar.write("OC RAW:", oc)

        else:
            st.warning("⚠️ No Option Chain Data")

    else:
        st.warning("⚠️ No Expiry Data")

except Exception as e:
    st.error(f"❌ Option Chain Error: {e}")

# =========================
# 6. STATUS SUMMARY
# =========================
st.subheader("6. System Status")

st.success("✅ Dashboard Running")

# =========================
# REFRESH BUTTON
# =========================
if st.button("🔄 Refresh"):
    st.cache_data.clear()
    st.rerun()
