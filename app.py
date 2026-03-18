import streamlit as st

from dashboard.header import show_header
from dashboard.navbar import show_navbar

st.set_page_config(page_title="Trading Dashboard", layout="wide")

# HEADER
show_header()

# NAVBAR
tab = show_navbar()

# LOAD SCREEN
if tab == "Stocks":
    from dashboard.stocks import show_stocks
    show_stocks()
