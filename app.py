import streamlit as st
import pandas as pd

# Modules
from dhan_data.market_quote import get_ltp
from dhan_data.historical_data import get_historical
from dhan_data.chart import get_candle_data, plot_candle
from dhan_data.expiry import get_expiry
from dhan_data.option_chain import get_option_chain
from core.token_manager import get_token, get_headers

st.set_page_config(layout="wide")
st.title("🔍 Dhan Full Debug Dashboard")

# =========================
# 1. TOKEN CHECK
# =========================
st.subheader("1. Token Check")

try:
    token = get_token()
    headers = get_headers()
    st.success("✅ Token Loaded")
    st.write(headers)
except Exception as e:
    st.error(f"❌ Token Error: {e}")

# =========================
# 2. LTP CHECK
# =========================
st.subheader("2. LTP Check")

try:
    ltp = get_ltp(2885, "NSE_EQ")
    st.success(f"✅ LTP: {ltp}")
except Exception as e:
    st.error(f"❌ LTP Error: {e}")

# =========================
# 3. HISTORICAL CHECK
# =========================
st.subheader("3. Historical Check")

try:
    hist = get_historical(2885, "NSE_EQ")
    st.write("RAW DATA:", hist)

    if hist:
        st.success("✅ Historical Data Loaded")
    else:
        st.warning("⚠️ No Historical Data")
except Exception as e:
    st.error(f"❌ Historical Error: {e}")

# =========================
# 4. CANDLE CHECK
# =========================
st.subheader("4. Candle Check")

try:
    df = get_candle_data(2885, "NSE_EQ")

    if df is not None:
        st.write("DataFrame Preview:", df.head())

        fig, trend = plot_candle(df)
        st.success(f"Trend: {trend}")
        st.plotly_chart(fig)
    else:
        st.warning("⚠️ No Candle Data")

except Exception as e:
    st.error(f"❌ Candle Error: {e}")

# =========================
# 5. OPTION CHAIN CHECK
# =========================
st.subheader("5. Option Chain Check")

try:
    exp_list = get_expiry(13, "IDX_I")

    if exp_list:
        expiry = exp_list[0]
        st.write("Expiry:", expiry)

        oc = get_option_chain(13, expiry, "IDX_I")
        st.write("Option Chain RAW:", oc)

        if oc:
            st.success("✅ Option Chain Loaded")
        else:
            st.warning("⚠️ No OC Data")

    else:
        st.warning("⚠️ No Expiry Data")

except Exception as e:
    st.error(f"❌ Option Chain Error: {e}")

# =========================
# 6. FINAL STATUS
# =========================
st.success("🚀 Debug Scan Complete")

# =========================
# REFRESH
# =========================
if st.button("Refresh"):
    st.cache_data.clear()
    st.rerun()
