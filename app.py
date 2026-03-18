import streamlit as st

from core.api import fetch_data
from dashboard.header import show_header

st.set_page_config(page_title="Dhan Header", layout="wide")

data = fetch_data()

# ONLY HEADER
show_header(data)
