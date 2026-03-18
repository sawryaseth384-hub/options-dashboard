import streamlit as st
import requests

st.title("📊 DHAN DATA DASHBOARD")

# 🔐 Secrets
CLIENT_ID = st.secrets["CLIENT_ID"]
ACCESS_TOKEN = st.secrets["ACCESS_TOKEN"]

# 🔘 Button
if st.button("Fetch Data"):

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
    data = res.json()

    # ✅ RAW DATA
    st.subheader("📡 RAW DATA")
    st.json(data)
