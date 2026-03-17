import streamlit as st
import pandas as pd

from ai_engine.market_quote import MarketQuote
from ai_engine.data_processor import process_quote
from ai_engine.option_chain import OptionChain
from ai_engine.historical_data import HistoricalData

from streamlit_autorefresh import st_autorefresh

# INIT
mq = MarketQuote()
oc = OptionChain()
hd = HistoricalData()

# UI
st.set_page_config(page_title="AI Trading Dashboard", layout="wide")
st.title("🚀 AI Options Trading Dashboard")

# SIDEBAR
st.sidebar.header("Settings")

refresh_time = st.sidebar.slider("Refresh Time (sec)", 1, 10, 3)

mode = st.sidebar.selectbox(
    "Select Data",
    ["Live Market", "Option Chain", "Historical"]
)

st_autorefresh(interval=refresh_time * 1000)

# ==============================
# 🔥 1. LIVE MARKET
# ==============================
if mode == "Live Market":

    st.subheader("📊 Live Market Data")

    instruments = {
        "NSE_EQ": ["11536"]
    }

    raw_data = mq.get_data(instruments)   # ✅ FIX

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

    expiries = oc.get_expiry_list()   # ✅ FIX

    if not expiries:
        st.error("No expiry found")
        st.stop()

    expiry = st.selectbox("Select Expiry", expiries)

    data = oc.get_data()   # already auto expiry use karta hai

    if "error" in data:
        st.error(data["error"])
        st.stop()

    oc_data = data["data"]["data"]["oc"]

    rows = []

    for strike, value in oc_data.items():
        ce = value.get("ce", {})
        pe = value.get("pe", {})

        rows.append({
            "strike": strike,
            "ce_oi": ce.get("oi", 0),
            "ce_ltp": ce.get("last_price", 0),
            "pe_oi": pe.get("oi", 0),
            "pe_ltp": pe.get("last_price", 0),
        })

    df = pd.DataFrame(rows)

    st.dataframe(df, use_container_width=True)

    # 🔥 PCR
    if df["ce_oi"].sum() != 0:
        pcr = df["pe_oi"].sum() / df["ce_oi"].sum()
        st.metric("PCR", round(pcr, 2))


# ==============================
# 🔥 3. HISTORICAL
# ==============================
elif mode == "Historical":

    st.subheader("📊 Historical Data")

    df = hd.get_intraday_data("11536")

    if df.empty:
        st.warning("No data")
        st.stop()

    st.line_chart(df["close"])
    st.dataframe(df.tail(), use_container_width=True)
