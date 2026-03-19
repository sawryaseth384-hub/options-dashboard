import streamlit as st
from streamlit_autorefresh import st_autorefresh

# 🔥 IMPORT FIX
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from core import dhan_api
from utils import helpers


# 🔥 PAGE CONFIG
st.set_page_config(page_title="Dhan AI Options Dashboard", layout="wide")

st.title("📈 Dhan AI Options Dashboard")


# 🔁 AUTO REFRESH
refresh = st.selectbox("Auto Refresh (seconds)", [0, 5, 10, 30])

if refresh > 0:
    st_autorefresh(interval=refresh * 1000, key="refresh")


# 🔥 DEBUG TOGGLE
show_debug = st.sidebar.checkbox("🔧 Show Debug Info")


# ✅ EXPIRY FETCH (VALID ONLY)
expiry_list = dhan_api.get_valid_expiries()

if show_debug:
    st.sidebar.write("📆 Valid Expiries:", expiry_list)


# ❌ अगर expiry नहीं मिली
if not expiry_list:
    st.error("❌ No valid expiry available (API issue)")
    st.stop()


# 🔥 SELECT EXPIRY
selected_expiry = st.selectbox("Select Expiry", expiry_list)


# 🔥 OPTION CHAIN FETCH
raw_data = dhan_api.get_option_chain(selected_expiry)

if show_debug:
    st.sidebar.write("📊 RAW OPTION:", raw_data)


if not raw_data or raw_data.get("status") != "success":
    st.error("❌ Option chain failed (Invalid expiry / API issue)")
    st.stop()


# 🔥 PROCESS DATA
df, spot = helpers.process_option_data(raw_data)


if df.empty:
    st.warning("⚠️ No option data available")
    st.stop()


# 🔥 DISPLAY
st.metric("📊 Spot Price", f"₹{spot:,.2f}")

st.dataframe(df, use_container_width=True)
