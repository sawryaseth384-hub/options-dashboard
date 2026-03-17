import streamlit as st

from ai_engine.market_quote import get_market_quote
from ai_engine.option_chain import get_option_chain

st.title("AI Options Dashboard")

quote = get_market_quote()
st.subheader("Market Quote")
st.write(quote)

option_data = get_option_chain()

st.subheader("Option Chain Data")
st.write(option_data)
