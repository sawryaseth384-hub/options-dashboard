import streamlit as st

# IMPORT UI
from dashboard.header import show_header
from dashboard.navbar import show_navbar
from dashboard.stocks import show_stocks
from dashboard.options import show_options
from dashboard.futures import show_futures

st.set_page_config(page_title="Pro Dashboard", layout="wide")

# HEADER
show_header()

# NAVBAR
tab = show_navbar()

# LOAD PAGE
if tab == "Stocks":
    show_stocks()

elif tab == "Options":
    show_options()

elif tab == "Futures":
    show_futures()
