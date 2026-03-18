import streamlit as st
from live_ws import DhanLive
import time

st.set_page_config(page_title="AI Trading Dashboard", layout="wide")

st.title("🚀 LIVE DHAN MARKET FEED")

# ✅ Secrets
CLIENT_ID = st.secrets["CLIENT_ID"]
ACCESS_TOKEN = st.secrets["ACCESS_TOKEN"]

st.success("✅ Credentials Loaded")

# 🔥 Start WebSocket (only once)
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

# 🔥 LIVE LOOP
while True:
    data = st.session_state.ws.latest_data

    if data:

        try:
            segment = list(data["data"].keys())[0]
            instrument = list(data["data"][segment].keys())[0]
            d = data["data"][segment][instrument]

            ltp = d.get("last_price", 0)
            oi = d.get("oi", 0)
            vol = d.get("volume", 0)

            # 🎯 Metrics
            ltp_box.metric("📈 LTP", ltp)
            oi_box.metric("📊 OI", oi)
            vol_box.metric("📦 Volume", vol)

            # 🔍 Raw Data
            json_box.json(data)

        except Exception as e:
            st.error(f"Parsing Error: {e}")

    time.sleep(1)
