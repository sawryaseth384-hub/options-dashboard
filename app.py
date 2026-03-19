import streamlit as st
import time
from core.api import fetch_data
from dashboard.header import show_header

st.set_page_config(page_title="Dhan Live Dashboard", layout="wide")

# 🔥 AUTO REFRESH LOOP
placeholder = st.empty()

while True:
    data = fetch_data()

    with placeholder.container():
        show_header(data)

    time.sleep(2)   # हर 2 सेकंड refresh
