import requests
import streamlit as st
from core.token_manager import get_headers

BASE_URL = "https://api.dhan.co/v2"

def map_exchange(segment):
    if segment == "IDX_I":
        return "NSE_EQ"
    return "NSE_FNO"

def get_ltp(security_id, segment):
    exchange = map_exchange(segment)
    payload = {"NSE_EQ": [], "NSE_FNO": []}
    payload[exchange].append(int(security_id))
    try:
        res = requests.post(
            f"{BASE_URL}/marketfeed/ltp",
            headers=get_headers(),
            json=payload,
            timeout=10
        )
        data = res.json()
        return data.get("data", {}).get(exchange, {}).get(str(security_id), {}).get("last_price", 0)
    except Exception as e:
        st.error(f"LTP Error: {e}")
        return 0
