import streamlit as st
from streamlit_autorefresh import st_autorefresh

# 🔥 IMPORT FIX (FINAL)
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# ✅ SAFE IMPORT
from core import dhan_api
from utils import helpers


# 🔥 PAGE CONFIG
st.set_page_config(page_title="Dhan AI Options Dashboard", layout="wide")

st.title("📈 Dhan AI Options Dashboard")


# 🔁 AUTO REFRESH
refresh = st.selectbox("Auto Refresh (seconds)", [0, 5, 10, 30])

if refresh > 0:
    st_autorefresh(interval=refresh * 1000, key="refresh")


# 🔥 EXPIRY FETCH
expiry_list = dhan_api.get_expiry_list()

# DEBUG
st.write("📆 EXPIRIES:", expiry_list)


# ❌ अगर expiry नहीं आई
if not expiry_list:
    st.error("❌ Expiry load failed (API / Secret issue)")
    st.stop()


# 🔥 SELECT EXPIRY
selected_expiry = st.selectbox("Select Expiry", expiry_list)


# 🔥 OPTION CHAIN FETCH
raw_data = dhan_api.get_option_chain(selected_expiry)

# DEBUG
st.write("📊 RAW OPTION DATA:", raw_data)


if not raw_data or raw_data.get("status") != "success":
    st.error("❌ Option chain not received / API failed")
    st.stop()


# 🔥 PROCESS DATA
df, spot = helpers.process_option_data(raw_data)


if df.empty:
    st.warning("⚠️ No option data available")
    st.stop()


# 🔥 DISPLAY
st.metric("📊 Spot Price", f"₹{spot:,.2f}")

st.dataframe(df, use_container_width=True)
