import streamlit as st
import requests

st.set_page_config(layout="wide")

st.title("📊 DHAN SIMPLE DASHBOARD")

# 🔐 Secrets
CLIENT_ID = st.secrets["CLIENT_ID"]
ACCESS_TOKEN = st.secrets["ACCESS_TOKEN"]

# 🔗 API CALL
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


# 🚀 BUTTON
if st.button("Fetch Data"):

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

        st.success("✅ Data Loaded")
        st.dataframe(rows)

    else:
        st.error("❌ API Error")
