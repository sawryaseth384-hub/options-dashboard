import streamlit as st
from core.api import fetch_data
from dashboard.header import show_header

# 🔥 Page config (always top pe)
st.set_page_config(
    page_title="Dhan Pro Dashboard",
    layout="wide"
)

# 🔥 DATA FETCH
try:
    data = fetch_data()
except Exception as e:
    st.error(f"Data Error: {e}")
    data = []

# 🔥 DEBUG (optional - hata sakta hai baad me)
# st.write(data)

# 🔥 HEADER
show_header(data)
