import streamlit as st
from streamlit_autorefresh import st_autorefresh

# 🔥 IMPORT FIX
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from core import dhan_api
from utils import helpers
from utils.debug import render_debug_panel


# 🔥 PAGE CONFIG
st.set_page_config(page_title="Dhan AI Options Dashboard", layout="wide")

st.title("📈 Dhan AI Options Dashboard")


# 🔁 AUTO REFRESH
refresh = st.selectbox("Auto Refresh (seconds)", [0, 5, 10, 30])

if refresh > 0:
    st_autorefresh(interval=refresh * 1000, key="refresh")


# =========================
# 🔥 EXPIRY FETCH
# =========================
expiry_list = []

try:
    expiry_list = dhan_api.get_valid_expiries()
except Exception as e:
    st.error(f"❌ Expiry Error: {e}")

if not expiry_list:
    st.warning("⚠️ No expiry data")


# 🔥 SELECT EXPIRY
selected_expiry = None
if expiry_list:
    selected_expiry = st.selectbox("Select Expiry", expiry_list)


# =========================
# 🔥 OPTION CHAIN FETCH
# =========================
raw_data = None

if selected_expiry:
    try:
        raw_data = dhan_api.get_option_chain(selected_expiry)
    except Exception as e:
        st.error(f"❌ Option Chain Error: {e}")

if raw_data and raw_data.get("status") != "success":
    st.error("❌ Option chain failed")


# =========================
# 🔥 PROCESS DATA
# =========================
df = None
spot = 0

if raw_data and raw_data.get("status") == "success":
    try:
        df, spot = helpers.process_option_data(raw_data)
    except Exception as e:
        st.error(f"❌ Data Processing Error: {e}")


# =========================
# 📊 MAIN METRICS
# =========================
col1, col2, col3, col4 = st.columns(4)

# Spot (Always show)
with col1:
    st.metric("📊 Spot", f"₹{spot:,.2f}")


# PCR
pcr = 0
try:
    if df is not None:
        pcr = helpers.calculate_pcr(df)
except Exception as e:
    st.error(f"❌ PCR Error: {e}")

with col2:
    st.metric("📊 PCR", pcr)


# Support / Resistance
support, resistance = 0, 0
try:
    if df is not None:
        support, resistance = helpers.get_support_resistance(df)
except Exception as e:
    st.error(f"❌ SR Error: {e}")

with col3:
    st.metric("🟢 Support", support)

with col4:
    st.metric("🔴 Resistance", resistance)


# =========================
# 🚀 SIGNAL
# =========================
signal = "N/A"
try:
    signal = helpers.get_signal(pcr)
except Exception as e:
    st.error(f"❌ Signal Error: {e}")

st.subheader(f"🚀 Market Signal: {signal}")


# =========================
# 📊 OPTION CHAIN TABLE
# =========================
if df is not None:
    try:
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"❌ Table Error: {e}")
else:
    st.warning("⚠️ No data to display")


# =========================
# 🔧 DEBUG PANEL
# =========================
render_debug_panel()
