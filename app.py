import streamlit as st
import requests

st.set_page_config(page_title="Dhan API Test", layout="wide")

st.title("🚀 Dhan Data API Test")

# =========================
# 🔐 CONFIG (SECRETS)
# =========================

try:
    CLIENT_ID = st.secrets["CLIENT_ID"]
    ACCESS_TOKEN = st.secrets["ACCESS_TOKEN"]

    st.success("✅ Credentials Loaded")

except Exception as e:
    st.error("❌ Secrets missing")
    st.stop()


# =========================
# 🔥 INPUT
# =========================

st.subheader("📊 Instrument Input")

exchange = st.selectbox("Exchange", ["NSE_EQ", "NSE_FNO"])
security_id = st.text_input("Security ID", "49081")

# =========================
# 🚀 API CALL
# =========================

if st.button("🚀 Fetch Data"):

    url = "https://api.dhan.co/v2/marketfeed/quote"

    headers = {
        "access-token": ACCESS_TOKEN,
        "client-id": CLIENT_ID,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    try:
        payload = {
            exchange: [int(security_id)]
        }

        st.write("📤 Payload:", payload)

        res = requests.post(url, headers=headers, json=payload)

        st.write("📡 Status Code:", res.status_code)

        data = res.json()

        st.subheader("📥 Response")
        st.json(data)

        # =========================
        # 🔥 SIMPLE DATA CHECK
        # =========================

        if data.get("status") == "success":
            st.success("✅ API WORKING")

            segment = list(data["data"].keys())[0]
            instrument = list(data["data"][segment].keys())[0]

            ltp = data["data"][segment][instrument].get("last_price")

            st.metric("LTP", ltp)

        else:
            st.error("❌ API FAILED")
            st.write(data)

    except Exception as e:
        st.error(f"❌ ERROR: {e}")
        # 🔥 Extract data
if data.get("status") == "success":

    segment = list(data["data"].keys())[0]
    instrument = list(data["data"][segment].keys())[0]

    d = data["data"][segment][instrument]

    st.subheader("📊 Extracted Data")

    st.metric("LTP", d.get("last_price", 0))
    st.metric("OI", d.get("oi", 0))
    st.metric("Volume", d.get("volume", 0))
