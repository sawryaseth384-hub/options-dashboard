import streamlit as st
import requests
import pandas as pd
import time

st.set_page_config(layout="wide")
st.title("📊 DHAN PRO DASHBOARD")

# ---- SECRETS ----
CLIENT_ID = st.secrets["CLIENT_ID"]
ACCESS_TOKEN = st.secrets["ACCESS_TOKEN"]

# ---- API ----
def fetch_data():

    url = "https://api.dhan.co/v2/marketfeed/quote"

    headers = {
        "access-token": ACCESS_TOKEN,
        "client-id": CLIENT_ID,
        "Content-Type": "application/json"
    }

    payload = {
        "NSE_EQ": [11536],
        "NSE_FNO": [49081]
    }

    res = requests.post(url, headers=headers, json=payload)
    return res.json()

# ---- TOP CARDS ----
col1, col2, col3, col4 = st.columns(4)

col1.metric("NIFTY", "23,700", "+120")
col2.metric("BANKNIFTY", "55,200", "+300")
col3.metric("FINNIFTY", "20,100", "+80")
col4.metric("VIX", "18", "-0.5")

st.divider()

# ---- LIVE DATA ----
placeholder = st.empty()

while True:

    data = fetch_data()

    if data.get("status") == "success":

        rows = []

        for segment, items in data["data"].items():
            for sec_id, values in items.items():

                rows.append({
                    "Symbol": f"{segment}-{sec_id}",
                    "LTP": values.get("last_price"),
                    "Change": values.get("net_change", 0),
                    "OI": values.get("oi"),
                    "Volume": values.get("volume")
                })

        df = pd.DataFrame(rows)

        def color(val):
            return "color: green" if val > 0 else "color: red"

        with placeholder.container():

            st.success("🟢 Live Market Running")

            # Sidebar
            st.sidebar.title("📋 Watchlist")
            for r in rows:
                st.sidebar.write(f"{r['Symbol']} → ₹{r['LTP']}")

            # Table
            st.dataframe(
                df.style.applymap(color, subset=["Change"]),
                use_container_width=True
            )

    time.sleep(3)
