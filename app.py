import streamlit as st

# CORE
from core.api import fetch_data

# UI
from dashboard.header import show_header
from dashboard.header import show_header, check_alerts
from dashboard.navbar import show_navbar
from dashboard.stocks import show_stocks
from dashboard.options import show_options
from dashboard.futures import show_futures

st.set_page_config(page_title="Pro Dashboard", layout="wide")

# 🔥 DATA FETCH (MAIN ENGINE)
data = fetch_data()

# 🔥 HEADER
show_header(data)

# 🔥 NAVBAR
tab = show_navbar()

# 🔥 BODY
if tab == "Stocks":
    show_stocks(data)

elif tab == "Options":
    show_options(data)

elif tab == "Futures":
    show_futures(data)
