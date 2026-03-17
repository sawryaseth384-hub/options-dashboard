import streamlit as st

# AI ENGINE IMPORTS
from ai_engine.option_chain import get_option_chain
from ai_engine.market_quote import get_market_quote
from ai_engine.market_depth import get_market_depth

st.set_page_config(layout="wide")

st.title("📊 AI Options Dashboard (Dhan)")

# ===== SYMBOL INPUT =====
symbol = st.text_input("Enter Symbol", "NIFTY")

# ===== DATA FETCH BUTTON =====
if st.button("Get Data"):

    st.subheader("📈 Market Quote")
    quote = get_market_quote(symbol)
    st.write(quote)

    st.subheader("📊 Market Depth")
    depth = get_market_depth(symbol)
    st.write(depth)

    st.subheader("📉 Option Chain")
    option = get_option_chain(symbol)
    st.write(option)
