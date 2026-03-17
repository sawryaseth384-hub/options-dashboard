import streamlit as st
import requests
import os

# Token Render से आएगा
ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN")

headers = {
    "access-token": ACCESS_TOKEN
}

st.title("📊 Trading Dashboard")

# -------------------------
# MARKET DATA
# -------------------------
st.subheader("Market Data")

url = "https://api.dhan.co/v2/market-quote"

payload = {
    "IDX_I": ["NIFTY", "BANKNIFTY"]
}

response = requests.post(url, json=payload, headers=headers)

st.write(response.json())
