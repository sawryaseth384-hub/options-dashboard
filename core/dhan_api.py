import os
from dhanhq import dhanhq
import streamlit as st

client_id = os.getenv("DHAN_CLIENT_ID")
access_token = os.getenv("DHAN_ACCESS_TOKEN")

dhan = dhanhq(client_id, access_token)

@st.cache_data(ttl=10)
def get_expiry_list():
    try:
        res = dhan.expiry_list(
            under_security_id=13,
            under_exchange_segment="IDX_I"
        )
        return [x["expiry"] for x in res["data"]]
    except:
        return []

@st.cache_data(ttl=5)
def get_option_chain(expiry):
    try:
        res = dhan.option_chain(
            under_security_id=13,
            under_exchange_segment="IDX_I",
            expiry=expiry
        )
        return res["data"]
    except Exception as e:
        return []
