import streamlit as st
import requests
from streamlit_autorefresh import st_autorefresh

# 🔄 Auto refresh
st_autorefresh(interval=3000, key="refresh")

st.set_page_config(layout="wide")

# =========================
# 🔐 CONFIG
# =========================
CLIENT_ID = st.secrets["CLIENT_ID"]
ACCESS_TOKEN = st.secrets["ACCESS_TOKEN"]

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

# =========================
# 🔥 FETCH DATA
# =========================
res = requests.post(url, headers=headers, json=payload)
data = res.json()

if data.get("status") != "success":
    st.error("❌ API Error")
    st.stop()

# =========================
# 🎯 HEADER
# =========================
st.markdown("## 📊 DHAN PRO DASHBOARD")

# =========================
# 📈 TOP MARKET BAR
# =========================
st.markdown("### 📈 Market Overview")

col1, col2, col3, col4 = st.columns(4)

col1.metric("NIFTY", "23,700", "+120")
col2.metric("BANKNIFTY", "55,200", "+300")
col3.metric("FINNIFTY", "20,100", "+80")
col4.metric("VIX", "18", "-0.5")

st.markdown("---")

# =========================
# 🧩 LAYOUT (LEFT + RIGHT)
# =========================
left, right = st.columns([1, 3])

# =========================
# 📋 LEFT (WATCHLIST)
# =========================
with left:
    st.markdown("### 📋 Watchlist")

    for segment, items in data["data"].items():
        for sec_id, values in items.items():

            price = values.get("last_price", 0)
            change = values.get("net_change", 0)

            color = "green" if change >= 0 else "red"

            st.markdown(
                f"""
                <div style='padding:8px;border-bottom:1px solid #ddd'>
                    <b>{segment}-{sec_id}</b><br>
                    <span style='color:{color}'>₹ {price} ({change})</span>
                </div>
                """,
                unsafe_allow_html=True
            )

# =========================
# 📊 RIGHT (MAIN TABLE)
# =========================
with right:
    st.markdown("### 📊 Market Data")

    rows = []

    for segment, items in data["data"].items():
        for sec_id, values in items.items():

            change = values.get("net_change", 0)

            rows.append({
                "Symbol": f"{segment}-{sec_id}",
                "LTP": values.get("last_price"),
                "Change": change,
                "OI": values.get("oi"),
                "Volume": values.get("volume")
            })

    df = rows

    # 🔥 Table with color
    for r in df:
        r["Change"] = f"{r['Change']} 🔼" if r["Change"] >= 0 else f"{r['Change']} 🔽"

    st.dataframe(df, use_container_width=True)
