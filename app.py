import streamlit as st

from core.api import fetch_data
from dashboard.header import show_header, check_alerts
from dashboard.navbar import show_navbar
from dashboard.stocks import show_stocks
from dashboard.options import show_options
from dashboard.futures import show_futures

st.set_page_config(page_title="Dhan Pro Dashboard", layout="wide")

data = fetch_data()

show_header(data)

alerts = check_alerts(data)
for alert in alerts:
    st.warning(alert)

tab = show_navbar()

if tab == "Stocks":
    show_stocks(data)

elif tab == "Options":
    show_options(data)

elif tab == "Futures":
    show_futures(data)
