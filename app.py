import streamlit as st
import requests
import pandas as pd
from core.token_manager import get_headers
from dhan_data.instruments import get_symbol_data
from dhan_data.option_chain import get_option_chain

st.set_page_config(page_title="Dhan Options", layout="wide")

symbol = st.text_input("Symbol", value="NIFTY").upper()
if not symbol:
    st.stop()

security_id, segment = get_symbol_data(symbol)
if security_id is None:
    st.error("Invalid symbol")
    st.stop()

# Fetch expiry list
url = "https://api.dhan.co/v2/optionchain/expirylist"
payload = {"UnderlyingScrip": security_id, "UnderlyingSeg": "IDX_I"}
resp = requests.post(url, headers=get_headers(), json=payload)
if resp.status_code != 200 or resp.json().get("status") != "success":
    st.error("Expiry list failed")
    st.stop()

expiries = resp.json().get("data", [])
if not expiries:
    st.error("No expiry dates")
    st.stop()

expiry = st.selectbox("Expiry", expiries)
option_data = get_option_chain(security_id, segment, expiry)

if option_data and "data" in option_data and "oc" in option_data["data"]:
    oc = option_data["data"]["oc"]
    st.json(oc)
else:
    st.warning("Option chain empty")
