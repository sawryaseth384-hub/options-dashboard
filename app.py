import streamlit as st
from ai_engine.market_quote import get_market_quote

st.title("📊 Trading Dashboard")

data = get_market_quote()

# RAW DATA
st.write("RAW DATA 👇")
st.json(data)

# SAFE DISPLAY
try:
    nifty = data.get("data", {}).get("IDX_I", {}).get("13", {}).get("last_price", "N/A")
    banknifty = data.get("data", {}).get("IDX_I", {}).get("25", {}).get("last_price", "N/A")

    st.metric("NIFTY", nifty)
    st.metric("BANKNIFTY", banknifty)

except:
    st.error("Data error")
