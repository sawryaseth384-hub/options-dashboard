import streamlit as st
from streamlit_autorefresh import st_autorefresh

# 🔥 IMPORT FIX
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from core import dhan_api
from utils import helpers
from utils.debug import render_project_status


# 🔥 PAGE CONFIG
st.set_page_config(page_title="Dhan AI Options Dashboard", layout="wide")

st.title("📈 Dhan AI Options Dashboard")


# 🔁 AUTO REFRESH
refresh = st.selectbox("Auto Refresh (seconds)", [0, 5, 10, 30])

if refresh > 0:
    st_autorefresh(interval=refresh * 1000, key="refresh")


# 🔧 DEBUG TOGGLE
show_debug = st.sidebar.checkbox("🔧 Show Debug Info")


# =========================
# 🔥 EXPIRY FETCH
# =========================
expiry_list = dhan_api.get_valid_expiries()

if show_debug:
    st.sidebar.write("📆 Valid Expiries:", expiry_list)

if not expiry_list:
    st.error("❌ No valid expiry available (API issue)")
    st.stop()


# 🔥 SELECT EXPIRY (nearest default)
selected_expiry = st.selectbox(
    "Select Expiry",
    expiry_list,
    index=0
)


# =========================
# 🔥 OPTION CHAIN FETCH
# =========================
raw_data = dhan_api.get_option_chain(selected_expiry)

if show_debug:
    st.sidebar.write("📊 RAW OPTION:", raw_data)

if not raw_data or raw_data.get("status") != "success":
    st.error("❌ Option chain failed (Invalid expiry / API issue)")
    st.stop()


# =========================
# 🔥 PROCESS DATA
# =========================
df, spot = helpers.process_option_data(raw_data)

if df.empty:
    st.warning("⚠️ No option data available")
    st.stop()


# =========================
# 📊 MAIN METRICS
# =========================
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("📊 Spot", f"₹{spot:,.2f}")

# 🔥 PCR
try:
    pcr = helpers.calculate_pcr(df)
    st.session_state["pcr_done"] = True
except:
    pcr = 0
    st.session_state["pcr_done"] = False

with col2:
    st.metric("📊 PCR", pcr)


# 🔥 SUPPORT / RESISTANCE
try:
    support, resistance = helpers.get_support_resistance(df)
    st.session_state["sr_done"] = True
except:
    support, resistance = 0, 0
    st.session_state["sr_done"] = False

with col3:
    st.metric("🟢 Support", support)

with col4:
    st.metric("🔴 Resistance", resistance)


# =========================
# 🚀 SIGNAL
# =========================
try:
    signal = helpers.get_signal(pcr)
except:
    signal = "N/A"

st.subheader(f"🚀 Market Signal: {signal}")


# =========================
# 📊 OPTION CHAIN TABLE
# =========================
st.dataframe(df, use_container_width=True)


# =========================
# 🐛 DEBUG INFO
# =========================
if show_debug:
    st.sidebar.markdown("### 🐛 Debug Info")
    st.sidebar.write("Selected Expiry:", selected_expiry)
    st.sidebar.write("Spot:", spot)
    st.sidebar.write("Rows:", len(df))


# =========================
# 📊 PROJECT STATUS TRACKER
# =========================
render_project_status()
