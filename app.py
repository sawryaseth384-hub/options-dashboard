import streamlit as st
from live_ws import DhanLive
import time

st.set_page_config(page_title="Live Dhan Dashboard", layout="wide")

st.title("🚀 LIVE DHAN MARKET FEED")

# ✅ Secrets
CLIENT_ID = st.secrets["CLIENT_ID"]
ACCESS_TOKEN = st.secrets["ACCESS_TOKEN"]

st.success("✅ Credentials Loaded")

# 🔥 Start WebSocket only once
if "ws" not in st.session_state:
    st.session_state.ws = DhanLive(CLIENT_ID, ACCESS_TOKEN)
    st.session_state.ws.start()

st.success("🟢 Live Connected")

# 🔥 UI placeholders
col1, col2, col3 = st.columns(3)

ltp_box = col1.empty()
oi_box = col2.empty()
vol_box = col3.empty()

json_box = st.empty()

# 🔥 SAFE LOOP
for _ in range(1000):

    data = st.session_state.ws.latest_data

    if data:
        try:
            segment = list(data["data"].keys())[0]
            instrument = list(data["data"][segment].keys())[0]
            d = data["data"][segment][instrument]

            ltp = d.get("last_price", 0)
            oi = d.get("oi", 0)
            vol = d.get("volume", 0)

            ltp_box.metric("📈 LTP", ltp)
            oi_box.metric("📊 OI", oi)
            vol_box.metric("📦 Volume", vol)

            json_box.json(data)

        except Exception as e:
            st.warning(f"⏳ Waiting for proper data... {e}")

    else:
        st.warning("⏳ Waiting for live data...")

    time.sleep(1)
