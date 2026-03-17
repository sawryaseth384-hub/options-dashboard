import streamlit as st
import json

from ai_engine.market_quote import get_market_quote
from ai_engine.option_chain import get_option_chain
from ai_engine.market_depth import get_market_depth
from ai_engine.live_market_feed import get_live_market_feed
from ai_engine.historical_data import get_historical_data
from ai_engine.instrument_list import get_instrument_list

st.set_page_config(layout="wide")

st.title("🔥 DATA WAR ROOM")

# ---------------- FUNCTION ----------------
def show_section(title, func):

    st.subheader(title)

    try:
        data = func()

        col1, col2 = st.columns([3,1])

        with col1:
            st.json(data)

        with col2:
            st.success("✅ OK")

    except Exception as e:

        col1, col2 = st.columns([3,1])

        with col1:
            st.error(str(e))

        with col2:
            st.error("❌ ERROR")

    st.divider()


# ---------------- DASHBOARD ----------------

show_section("📊 Market Quote", get_market_quote)

show_section("📈 Option Chain", get_option_chain)

show_section("📉 Market Depth", get_market_depth)

show_section("⚡ Live Market Feed", get_live_market_feed)

show_section("📅 Historical Data", get_historical_data)

show_section("📜 Instrument List", get_instrument_list)
