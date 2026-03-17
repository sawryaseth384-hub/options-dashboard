import streamlit as st


from services.option_chain import get_option_chain
from services.historical_data import get_historical_data
from services.instrument_list import get_instrument_list
from services.market_depth import get_market_depth
from services.live_market_feed import get_live_market_feed

st.set_page_config(layout="wide")

st.title("🔥 DATA WAR ROOM")

# Market Quote
st.header("📊 Market Quote")
st.json(get_market_quote())

# Option Chain
st.header("📈 Option Chain")
st.json(get_option_chain())

# Historical
st.header("📅 Historical Data")
st.json(get_historical_data())

# Instrument List
st.header("📜 Instrument List")
st.json(get_instrument_list())

# Market Depth
st.header("📉 Market Depth")
st.json(get_market_depth())

# Live Feed
st.header("⚡ Live Market Feed")

live = get_live_market_feed()

for msg in live["messages"]:
    st.text(msg)
