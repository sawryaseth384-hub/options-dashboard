import streamlit as st
import os
import requests

st.title("AI Options Trading Dashboard")

# Get credentials from environment variables
client_id = os.getenv("DHAN_CLIENT_ID")
access_token = os.getenv("DHAN_ACCESS_TOKEN")

# Debug (temporary)
st.write("Client ID Loaded:", client_id)

url = "https://api.dhan.co/v2/marketfeed/ltp"

headers = {
    "access-token": access_token,
    "client-id": client_id,
    "Content-Type": "application/json"
}

payload = {
    "NSE_EQ": [13]   # 13 = NIFTY
}

try:
    response = requests.post(url, json=payload, headers=headers)
    data = response.json()

    st.subheader("API Response:")
    st.json(data)

    if data.get("status") == "success":
        nifty_price = data["data"]["NSE_EQ"]["13"]["last_price"]
        st.metric("NIFTY LTP", nifty_price)

    else:
        st.error("API returned error")

except Exception as e:
    st.error(f"Error: {e}")
