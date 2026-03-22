import requests
import streamlit as st
import time

BASE_URL = "https://api.dhan.co/v2"
_last_call_time = 0

def get_headers():
    return {
        "access-token": st.secrets["ACCESS_TOKEN"],
        "client-id": st.secrets["CLIENT_ID"],
        "Content-Type": "application/json"
    }

def map_api_segment(segment):
    """Convert internal segment (e.g., 'I') to API‑expected segment (e.g., 'IDX_I')."""
    if segment in ["I", "IDX_I"]:
        return "IDX_I"
    elif segment in ["D", "NSE_FNO"]:
        return "NSE_FNO"
    else:
        return "NSE_EQ"

def get_expiry(security_id, segment):
    global _last_call_time
    now = time.time()
    wait = max(0, 1 - (now - _last_call_time))
    if wait > 0:
        time.sleep(wait)
    _last_call_time = time.time()

    url = f"{BASE_URL}/optionchain/expirylist"
    api_segment = map_api_segment(segment)
    payload = {
        "UnderlyingScrip": int(security_id),
        "UnderlyingSeg": api_segment
    }

    # DEBUG: print payload
    st.write("### Expiry API Payload")
    st.json(payload)

    try:
        res = requests.post(url, headers=get_headers(), json=payload, timeout=10)
        data = res.json()
        st.write("### Expiry API Response")
        st.json(data)

        if not data or data.get("status") != "success":
            st.error(f"Expiry API error: {data}")
            return []
        return data.get("data", [])
    except Exception as e:
        st.error(f"Expiry request failed: {e}")
        return []
