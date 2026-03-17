import streamlit as st
import pandas as pd

# 🔹 AI ENGINE IMPORT
from ai_engine.market_quote import MarketQuote
from ai_engine.data_processor import process_quote

# 🔹 INIT API
mq = MarketQuote()

# 🔹 PAGE CONFIG
st.set_page_config(page_title="Options Dashboard", layout="wide")

st.title("📊 Live Options Dashboard")
st.markdown("Real-time data from Dhan API")

# 🔹 SIDEBAR
st.sidebar.header("Settings")

refresh_time = st.sidebar.slider("Refresh Time (sec)", 1, 10, 2)

# 🔹 INSTRUMENT INPUT (future expand)
instrument_input = st.sidebar.text_input(
    "Enter Security ID (comma separated)",
    "49081"
)

instrument_list = [int(x.strip()) for x in instrument_input.split(",")]

instruments = {
    "NSE_FNO": instrument_list
}

# 🔹 AUTO REFRESH
from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=refresh_time * 1000)

# 🔹 FETCH DATA
raw_data = mq.get_quote(instruments)

# 🔴 ERROR HANDLE
if raw_data.get("status") != "success":
    st.error("❌ API Error: Check Token / Client ID")
    st.write(raw_data)
    st.stop()

# 🔹 PROCESS DATA
processed = process_quote(raw_data)

if not processed:
    st.warning("⚠️ No Data Received")
    st.stop()

df = pd.DataFrame(processed)

# 🔹 METRICS
st.subheader("📈 Key Metrics")

col1, col2, col3 = st.columns(3)

col1.metric("LTP", df["ltp"].iloc[0])
col2.metric("OI", df["oi"].iloc[0])
col3.metric("Volume", df["volume"].iloc[0])

st.divider()

# 🔹 TABLE
st.subheader("📋 Market Data")
st.dataframe(df, use_container_width=True)

st.divider()

# 🔹 CHART
st.subheader("📊 Price Chart")
st.line_chart(df["ltp"])

# 🔹 RAW DATA (DEBUG)
with st.expander("🔍 Raw API Data"):
    st.json(raw_data)
