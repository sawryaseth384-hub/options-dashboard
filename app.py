import streamlit as st
import os
import requests

st.title("AI Options Trading Dashboard")

client_id = os.getenv("DHAN_CLIENT_ID")
access_token = os.getenv("DHAN_ACCESS_TOKEN")

url = "https://api.dhan.co/v2/marketfeed/ltp"

headers = {
    "access-token": access_token,
    "client-id": client_id,
    "Content-Type": "application/json"
}

payload = {
    "NSE_EQ": [13]
}

try:
    response = requests.post(url, json=payload, headers=headers)
    data = response.json()

    st.write("API Response:", data)

    if data["status"] == "success":
        nifty = data["data"]["NSE_EQ"]["13"]["last_price"]
        st.metric("NIFTY LTP", nifty)

    else:
        st.error("API returned error")

except Exception as e:
    st.error(e)
