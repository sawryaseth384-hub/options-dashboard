import streamlit as st
from core.api import fetch_data
from dashboard.header import show_header

st.set_page_config(page_title="Dhan Pro", layout="wide")

data = fetch_data()

show_header(data)
