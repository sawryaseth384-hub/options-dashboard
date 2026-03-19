import streamlit as st
from streamlit_autorefresh import st_autorefresh

# 🔥 PATH FIX
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# ✅ IMPORTS
from core import dhan_api
from utils import helpers
from utils.debug import DebugManager

# 🔥 DEBUG INIT
debug = DebugManager()

# 🔥 PAGE CONFIG
st.set_page_config(page_title="Dhan AI Options Dashboard", layout="wide")

st.title("📈 Dhan AI Options Dashboard")

# ================================
# 🔁 AUTO REFRESH
# ================================
refresh = st.selectbox("Auto Refresh (seconds)", [0, 5, 10, 30])

if refresh > 0:
    st_autorefresh(interval=refresh * 1000, key="refresh")

# ================================
# 🔐 SECRETS CHECK
# ================================
try:
    st.secrets["CLIENT_ID"]
    st.secrets["ACCESS_TOKEN"]
    debug.set_status("Secrets", True)
except:
    debug.set_status("Secrets", False)
    debug.log("ERROR", "Secrets missing")

# ================================
# 📆 EXPIRY FETCH
# ================================
try:
    expiry_list = dhan_api.get_expiry_list()

    debug.set_api("Expiry List", expiry_list[:5] if expiry_list else [])
    debug.set_status("Expiry API", True)
    debug.log("SUCCESS", f"{len(expiry_list)} expiries fetched")

except Exception as e:
    expiry_list = []
    debug.set_status("Expiry API", False)
    debug.log("ERROR", "Expiry fetch failed", str(e))

# 🔍 DEBUG VIEW
st.write("📆 EXPIRIES:", expiry_list)

# ❌ अगर expiry नहीं आई
if not expiry_list:
    st.error("❌ Expiry load failed")
    debug.render()
    st.stop()

# ================================
# 🔥 EXPIRY SELECT
# ================================
selected_expiry = st.selectbox("Select Expiry", expiry_list)

debug.set_status("Selected Expiry", selected_expiry)

# ================================
# 📊 OPTION CHAIN FETCH
# ================================
try:
    raw_data = dhan_api.get_option_chain(selected_expiry)

    debug.set_api("Option Chain", raw_data)

    if raw_data and raw_data.get("status") == "success":
        debug.set_status("Option Chain", True)
        debug.log("SUCCESS", f"Option chain OK ({selected_expiry})")
    else:
        debug.set_status("Option Chain", False)
        debug.log("ERROR", "Invalid expiry / API failed", raw_data)

except Exception as e:
    raw_data = None
    debug.set_status("Option Chain", False)
    debug.log("ERROR", "Option chain crash", str(e))

# 🔍 DEBUG VIEW
st.write("📊 RAW OPTION DATA:", raw_data)

# ❌ अगर fail हुआ
if not raw_data or raw_data.get("status") != "success":
    st.error("❌ Option chain not received")
    debug.render()
    st.stop()

# ================================
# ⚙️ PROCESS DATA
# ================================
try:
    df, spot = helpers.process_option_data(raw_data)

    if df.empty:
        debug.log("WARNING", "Empty dataframe returned")
        st.warning("⚠️ No option data available")
        debug.render()
        st.stop()

    debug.log("SUCCESS", "Data processed successfully")

except Exception as e:
    debug.log("ERROR", "Processing failed", str(e))
    st.error("❌ Data processing failed")
    debug.render()
    st.stop()

# ================================
# 📊 DISPLAY
# ================================
st.metric("📊 Spot Price", f"₹{spot:,.2f}")

st.dataframe(df, use_container_width=True)

# ================================
# 🐛 DEBUG CONSOLE RENDER
# ================================
debug.render()
