import os
from dhanhq import dhanhq
from dotenv import load_dotenv

load_dotenv()

# 🔐 ENV VARIABLES
CLIENT_ID = os.getenv("DHAN_CLIENT_ID")
ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN")

# 🚀 DHAN OBJECT
dhan = dhanhq(CLIENT_ID, ACCESS_TOKEN)


# ✅ Expiry List
def get_expiry_list():
    try:
        res = dhan.expiry_list(
            under_security_id=13,
            under_exchange_segment="IDX_I"
        )
        return [x["expiry"] for x in res.get("data", [])]
    except Exception as e:
        import streamlit as st
        st.error(f"Expiry Error: {e}")
        return []


# ✅ Option Chain
def get_option_chain(expiry):
    try:
        res = dhan.option_chain(
            under_security_id=13,
            under_exchange_segment="IDX_I",
            expiry=str(expiry)
        )
        return res.get("data", [])
    except Exception as e:
        import streamlit as st
        st.error(f"Option Chain Error: {e}")
        return []
