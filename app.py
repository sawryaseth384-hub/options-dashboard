import streamlit as st
from dhanhq import dhanhq
import os

st.title("AI Options Trading Dashboard")

# Dhan credentials
client_id = os.getenv("DHAN_CLIENT_ID")
access_token = os.getenv("DHAN_ACCESS_TOKEN")

try:
    dhan = dhanhq(client_id, access_token)

    # Fetch NIFTY price
    data = dhan.get_market_feed({
        "NSE_EQ": [13]
    })

    nifty_price = data["NSE_EQ"]["13"]["last_price"]

    st.metric("NIFTY LTP", nifty_price)

except Exception as e:
    st.error(e)
