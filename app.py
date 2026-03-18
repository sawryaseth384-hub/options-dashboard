import streamlit as st
import requests
from streamlit_autorefresh import st_autorefresh

# 🔄 Auto refresh
st_autorefresh(interval=3000, key="refresh")

st.set_page_config(page_title="Dhan Dashboard", layout="wide")

st.title("📊 DHAN LIVE DASHBOARD")

# 🔐 Secrets
CLIENT_ID = st.secrets["CLIENT_ID"]
ACCESS_TOKEN = st.secrets["ACCESS_TOKEN"]

# 🔥 API
url = "https://api.dhan.co/v2/marketfeed/quote"

headers = {
    "access-token": ACCESS_TOKEN,
    "client-id": CLIENT_ID,
    "Content-Type": "application/json"
}

payload = {
    "NSE_EQ": [11536],
    "NSE_FNO": [49081, 49082]
}

# 🔁 API CALL
res = requests.post(url, headers=headers, json=payload)
data = res.json()

# ❌ Error check
if data.get("status") != "success":
    st.error("❌ API Error")
    st.write(data)
    st.stop()

# 🔥 PROCESS DATA
rows = []
total_oi = 0
total_volume = 0

for segment, items in data["data"].items():
    for sec_id, values in items.items():

        ltp = values.get("last_price", 0)
        oi = values.get("oi", 0)
        volume = values.get("volume", 0)

        total_oi += oi
        total_volume += volume

        rows.append({
            "Segment": segment,
            "SecurityID": sec_id,
            "Price": ltp,
            "OI": oi,
            "Volume": volume,
            "Buy": values.get("buy_quantity", 0),
            "Sell": values.get("sell_quantity", 0)
        })

# =========================
# 🔥 TOP DASHBOARD (LIKE DHAN)
# =========================

col1, col2, col3 = st.columns(3)

col1.metric("📈 Total OI", total_oi)
col2.metric("📊 Total Volume", total_volume)
col3.metric("📦 Instruments", len(rows))

st.markdown("---")

# =========================
# 📊 MAIN TABLE
# =========================

st.subheader("📊 LIVE MARKET DATA")

st.dataframe(rows, use_container_width=True)

# =========================
# 🔍 DETAIL VIEW
# =========================

st.markdown("---")
st.subheader("🔍 Detailed View")

for r in rows:
    with st.expander(f"{r['Segment']} - {r['SecurityID']}"):
        st.write(f"Price: {r['Price']}")
        st.write(f"OI: {r['OI']}")
        st.write(f"Volume: {r['Volume']}")
        st.write(f"Buy Qty: {r['Buy']}")
        st.write(f"Sell Qty: {r['Sell']}")
