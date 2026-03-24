import requests
import streamlit as st
from core.token_manager import get_headers

BASE_URL = "https://api.dhan.co/v2"

def get_ltp(security_id, segment):
    # Always use NSE_EQ – works for both indices and stocks
    exchange = "NSE_EQ"
    payload = {"NSE_EQ": [int(security_id)]}
    try:
        res = requests.post(
            f"{BASE_URL}/marketfeed/ltp",
            headers=get_headers(),
            json=payload,
            timeout=10
        )
        data = res.json()
        ltp = data.get("data", {}).get(exchange, {}).get(str(security_id), {}).get("last_price", 0)
        return ltp
    except Exception as e:
        st.error(f"LTP Error: {e}")
        return 0
