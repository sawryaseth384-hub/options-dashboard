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
st.title("🔬 Full Dhan Modules Scan")

# =========================
# TOKEN
# =========================
st.subheader("1. Token")

try:
    token = get_token()
    st.success("✅ Token OK")
except Exception as e:
    st.error(f"❌ Token Error: {e}")

# =========================
# SYMBOLS
# =========================
st.subheader("2. Symbols")

symbols = {
    "NIFTY": (13, "IDX_I"),
    "RELIANCE": (2885, "NSE_EQ"),
}

for name, (sec, seg) in symbols.items():
    st.write(f"{name}: {sec}, {seg}")

nifty_sec, nifty_seg = symbols["NIFTY"]

# =========================
# OPTION CHAIN
# =========================
st.subheader("3. Option Chain")

try:
    exp_list = get_expiry(nifty_sec, nifty_seg)

    if exp_list:
        expiry = exp_list[0]
        oc = get_option_chain(nifty_sec, expiry, nifty_seg)

        if oc and "data" in oc:
            spot = oc["data"].get("last_price")
            st.write(f"Spot: {spot}")
            st.success("✅ Option Chain Loaded")
        else:
            st.warning("⚠️ Option Chain Empty")

except Exception as e:
    st.error(f"❌ OC Error: {e}")

# =========================
# MARKET QUOTES (LTP)
# =========================
st.subheader("4. Market Quotes")

try:
    ltp = get_ltp(2885, "NSE_EQ")

    if ltp:
        st.success(f"RELIANCE LTP: {ltp}")
    else:
        st.warning("⚠️ LTP ZERO")

except Exception as e:
    st.error(f"❌ LTP Error: {e}")

# =========================
# HISTORICAL
# =========================
st.subheader("5. Historical Data")

try:
    hist = get_historical(2885, "NSE_EQ")

    if hist and len(hist.get("close", [])) > 0:
        st.success(f"Data Points: {len(hist['close'])}")
    else:
        st.warning("⚠️ No historical data")

except Exception as e:
    st.error(f"❌ Historical Error: {e}")

# =========================
# CANDLE
# =========================
st.subheader("6. Candlestick")

try:
    df = get_candle_data(2885, "NSE_EQ")

    if df is not None and len(df) > 1:
        fig, trend = plot_candle(df)
        st.write(f"Trend: {trend}")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("⚠️ No candle data")

except Exception as e:
    st.error(f"❌ Candle Error: {e}")

# =========================
# START DEPTH FEED
# =========================
try:
    from dhan_data.depth_feed import start_depth_feed, subscribe_depth

    if "depth_started" not in st.session_state:
        start_depth_feed()
        subscribe_depth(2885, "NSE_EQ")
        st.session_state.depth_started = True

except Exception as e:
    st.warning(f"Depth Init Issue: {e}")

# =========================
# DEBUG PANEL
# =========================
st.subheader("🛠 DEBUG PANEL")

# LTP DEBUG
st.write("### 📈 LTP STATUS")

try:
    ltp = get_ltp(2885, "NSE_EQ")

    if ltp and ltp != 0:
        st.success(f"✅ LTP OK: {ltp}")
    else:
        st.error("❌ LTP NOT WORKING")

except Exception as e:
    st.error(f"❌ LTP ERROR: {e}")

# DEPTH DEBUG
st.write("### 📊 DEPTH STATUS")

try:
    from dhan_data.depth_feed import get_depth

    depth = get_depth()

    if not depth:
        st.error("❌ Depth NOT STARTED")

    elif depth.get("bids") or depth.get("asks"):

        st.success("✅ Depth WORKING")

        col1, col2 = st.columns(2)

        with col1:
            st.write("📉 Bids")
            st.dataframe(pd.DataFrame(depth.get("bids", [])[:5]))

        with col2:
            st.write("📈 Asks")
            st.dataframe(pd.DataFrame(depth.get("asks", [])[:5]))

    else:
        st.warning("⚠️ Depth NO DATA")

except ImportError:
    st.error("❌ depth_feed.py missing")

except Exception as e:
    st.error(f"❌ Depth ERROR: {e}")

# =========================
# REFRESH
# =========================
if st.button("🔄 Refresh"):
    st.cache_data.clear()
    st.rerun()

st.success("✅ Scan Complete")
