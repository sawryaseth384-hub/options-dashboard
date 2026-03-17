import streamlit as st
from ai_engine.market_quote import get_market_quote

st.title("AI Options Dashboard")

data = get_market_quote()

st.write(data)
