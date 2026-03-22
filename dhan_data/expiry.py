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

def get_expiry(security_id, segment):
    global _last_call_time
    now = time.time()
    wait = max(0, 1 - (now - _last_call_time))
    if wait > 0:
        time.sleep(wait)
    _last_call_time = time.time()

    url = f"{BASE_URL}/optionchain/expirylist"
    payload = {
        "UnderlyingScrip": int(security_id),
        "UnderlyingSeg": segment
    }

    try:
        res = requests.post(url, headers=get_headers(), json=payload, timeout=10)
        data = res.json()

        # DEBUG: show full response in Streamlit
        st.write("### Expiry API Response")
        st.json(data)

        if not data or data.get("status") != "success":
            st.error(f"Expiry API error: {data}")
            return []
        return data.get("data", [])
    except Exception as e:
        st.error(f"Expiry request failed: {e}")
        return []
