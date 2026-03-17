import streamlit as st

from ai_engine.market_quote import get_market_quote
from ai_engine.option_chain import get_option_chain
from ai_engine.market_depth import get_market_depth
from ai_engine.live_market_feed import get_live_market_feed
from ai_engine.historical_data import get_historical_data
from ai_engine.instrument_list import get_instrument_list

st.set_page_config(layout="wide")

st.title("📡 DATA WAR ROOM")

# ---------------- MARKET QUOTE ----------------
st.header("📊 Market Quote")
quote = get_market_quote()
st.json(quote)

# ---------------- OPTION CHAIN ----------------
st.header("📈 Option Chain")
option = get_option_chain()
st.json(option)

# ---------------- MARKET DEPTH ----------------
st.header("📉 Market Depth")
depth = get_market_depth()
st.json(depth)

# ---------------- LIVE FEED ----------------
st.header("⚡ Live Market Feed")
live = get_live_market_feed()
st.json(live)

# ---------------- HISTORICAL ----------------
st.header("📅 Historical Data")
history = get_historical_data()
st.json(history)

# ---------------- INSTRUMENT LIST ----------------
st.header("📜 Instrument List")
inst = get_instrument_list()
st.json(inst)
