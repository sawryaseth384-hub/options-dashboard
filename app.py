import streamlit as st

from utils.config import ACCESS_TOKEN, CLIENT_ID, config
from ai_engine.market_quote import MarketQuote
from ai_engine.option_chain import OptionChain
from ai_engine.historical_data import HistoricalData

# -------------------------------
# PAGE SETUP
# -------------------------------
st.set_page_config(page_title="AI Trading Dashboard", layout="wide")

st.title("📊 AI Trading Dashboard")

# -------------------------------
# CONFIG STATUS
# -------------------------------
st.subheader("⚙️ Config Status")

if ACCESS_TOKEN:
    st.success("ACCESS_TOKEN Loaded ✅")
else:
    st.error("ACCESS_TOKEN Missing ❌")

if CLIENT_ID:
    st.success("CLIENT_ID Loaded ✅")
else:
    st.error("CLIENT_ID Missing ❌")

# DEBUG VIEW (optional)
with st.expander("🔍 Debug Config"):
    st.write(config)

# -------------------------------
# SAFE RUN FUNCTION
# -------------------------------
def safe_run(name, func):
    try:
        result = func()

        if isinstance(result, dict):
            if result.get("status") == "success":
                st.success(f"{name} ✅ Success")
            else:
                st.error(f"{name} ❌ Failed")

        st.json(result)

    except Exception as e:
        st.error(f"{name} ❌ Error: {str(e)}")

# -------------------------------
# CONTROL PANEL
# -------------------------------
st.subheader("🚀 AI Engine Control Panel")

col1, col2, col3 = st.columns(3)

# MARKET QUOTE
with col1:
    if st.button("📊 Market Quote"):
        safe_run(
            "Market Quote",
            lambda: MarketQuote().get_data({
                "NSE_FNO": [49081]
            })
        )

# OPTION CHAIN
with col2:
    if st.button("📈 Option Chain"):
        safe_run(
            "Option Chain",
            lambda: OptionChain().get_data()
        )

# HISTORICAL DATA
with col3:
    if st.button("📉 Historical Data"):
        safe_run(
            "Historical Data",
            lambda: HistoricalData().get_data()
        )

# -------------------------------
# LIVE MARKET TEST (SIMPLE)
# -------------------------------
st.subheader("🔍 Quick API Test")

if st.button("Test Dhan API"):
    import requests

    url = "https://api.dhan.co/v2/marketfeed/quote"

    headers = {
        "access-token": ACCESS_TOKEN,
        "client-id": CLIENT_ID,
        "Content-Type": "application/json"
    }

    payload = {
        "NSE_FNO": [49081]
    }

    try:
        res = requests.post(url, headers=headers, json=payload)
        st.write("Status Code:", res.status_code)
        st.json(res.json())

    except Exception as e:
        st.error(str(e))
