import streamlit as st
from ai_engine.data_fetcher import get_nifty_price

st.title("AI Options Dashboard")

data = get_nifty_price()

st.write(data)
