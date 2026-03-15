from dhanhq import dhanhq
import os
import streamlit as st

# credentials
client_id = os.getenv("DHAN_CLIENT_ID")
access_token = os.getenv("DHAN_ACCESS_TOKEN")

# connect
dhan = dhanhq(client_id, access_token)

# market feed request
data = dhan.get_market_feed({
    "NSE_EQ": [13]   # NIFTY
})

# extract price
nifty_price = data["NSE_EQ"]["13"]["last_price"]

# show on dashboard
st.metric("NIFTY LTP", nifty_price)
