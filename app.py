import streamlit as st
import requests
import os

st.title("AI Options Trading Dashboard")

client_id = os.getenv("DHAN_CLIENT_ID")
access_token = os.getenv("DHAN_ACCESS_TOKEN")

try:
    url = "https://api.dhan.co/v2/marketfeed/ltp"

    headers = {
        "access-token": access_token,
        "client-id": client_id,
        "Content-Type": "application/json"
    }

    payload = {
        "instruments": [
            {
                "exchangeSegment": "NSE_EQ",
                "securityId": "13"
            }
        ]
    }

    response = requests.post(url, headers=headers, json=payload)
    data = response.json()

    nifty_price = data["data"][0]["lastPrice"]

    st.metric("NIFTY LTP", nifty_price)

except Exception as e:
    st.error(e)
