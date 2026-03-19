import os
from dhanhq import dhanhq
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

CLIENT_ID = os.getenv("DHAN_CLIENT_ID")
ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN")

dhan = dhanhq(CLIENT_ID, ACCESS_TOKEN)


@st.cache_data(ttl=300)
def get_expiry_list():
    try:
        res = dhan.expiry_list(
            under_security_id=13,
            under_exchange_segment="IDX_I"
        )

        if res and "data" in res:
            return [x["expiry"] for x in res["data"] if "expiry" in x]

        return []

    except Exception as e:
        st.error(f"Expiry Error: {e}")
        return []


@st.cache_data(ttl=5)
def get_option_chain(expiry):
    try:
        return dhan.option_chain(
            under_security_id=13,
            under_exchange_segment="IDX_I",
            expiry=str(expiry)
        )
    except Exception as e:
        st.error(f"Option Chain Error: {e}")
        return None
