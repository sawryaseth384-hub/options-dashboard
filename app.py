import streamlit as st
import pandas as pd

# 🔥 IMPORT ALL MODULES
from ai_engine.market_quote import MarketQuote
from ai_engine.data_processor import process_quote
from ai_engine.option_chain import OptionChain
from ai_engine.historical_data import HistoricalData

# INIT
mq = MarketQuote()
oc = OptionChain()
hd = HistoricalData()

# UI CONFIG
st.set_page_config(page_title="AI Trading Dashboard", layout="wide")
st.title("🚀 AI Options Trading Dashboard")

# SIDEBAR
st.sidebar.header("Settings")

refresh_time = st.sidebar.slider("Refresh Time (sec)", 1, 10, 3)

# 🔥 SELECT MODE
mode = st.sidebar.selectbox(
    "Select Data",
    ["Live Market", "Option Chain", "Historical"]
)

# AUTO REFRESH
from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=refresh_time * 1000)

# ==============================
# 🔥 1. LIVE MARKET DATA
# ==============================
if mode == "Live Market":

    st.subheader("📊 Live Market Data")

    instruments = {
        "NSE_EQ": [11536]   # Reliance test
    }

    raw_data = mq.get_quote(instruments)

    if raw_data.get("status") != "success":
        st.error("API Error")
        st.stop()

    processed = process_quote(raw_data)

    if not processed:
        st.warning("No Data")
        st.stop()

    df = pd.DataFrame(processed)

    col1, col2, col3 = st.columns(3)

    col1.metric("LTP", df["ltp"].iloc[0])
    col2.metric("OI", df["oi"].iloc[0])
    col3.metric("Volume", df["volume"].iloc[0])

    st.dataframe(df, use_container_width=True)
    st.line_chart(df["ltp"])


# ==============================
# 🔥 2. OPTION CHAIN
# ==============================
elif mode == "Option Chain":

    st.subheader("📈 Option Chain")

    security_id = 13  # NIFTY

    # 🔥 GET EXPIRY LIST
    expiries = oc.get_expiry_list(security_id)

    if not expiries:
        st.error("No expiry found")
        st.stop()

    expiry = st.selectbox("Select Expiry", expiries)

    df = oc.get_chain(security_id, expiry)

    if df.empty:
        st.warning("No data")
        st.stop()

    st.dataframe(df, use_container_width=True)

    # 🔥 PCR CALCULATION
    pcr = df["pe_oi"].sum() / df["ce_oi"].sum()

    st.metric("PCR", round(pcr, 2))


# ==============================
# 🔥 3. HISTORICAL DATA
# ==============================
elif mode == "Historical":

    st.subheader("📊 Historical Data")

    df = hd.get_intraday_data(11536)

    if df.empty:
        st.warning("No data")
        st.stop()

    st.line_chart(df["close"])

    st.dataframe(df.tail(), use_container_width=True)
