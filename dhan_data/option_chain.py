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

def safe_post(url, payload, retries=2):
    global _last_call_time
    for attempt in range(retries):
        now = time.time()
        wait = max(0, 1 - (now - _last_call_time))
        if wait > 0:
            time.sleep(wait)
        try:
            res = requests.post(url, headers=get_headers(), json=payload, timeout=10)
            _last_call_time = time.time()
            data = res.json()
            if res.status_code != 200:
                st.error(f"HTTP {res.status_code}: {data}")
                return None
            if "808" in str(data):
                st.error("Token expired / invalid")
                return None
            return data
        except Exception as e:
            st.error(f"Request error: {e}")
            return None
    return None

def get_expiry_list(security_id, segment):
    url = f"{BASE_URL}/optionchain/expirylist"
    payload = {"UnderlyingScrip": int(security_id), "UnderlyingSeg": segment}
    data = safe_post(url, payload)
    if not data or data.get("status") != "success":
        st.error("Expiry list API failed")
        return []
    return data.get("data", [])

def get_option_chain(security_id, segment, expiry=None):
    if not expiry:
        expiries = get_expiry_list(security_id, segment)
        if not expiries:
            st.error("No expiry dates available")
            return None
        expiry = sorted(expiries)[0]
        st.info(f"Using nearest expiry: {expiry}")

    url = f"{BASE_URL}/optionchain"
    payload = {
        "UnderlyingScrip": int(security_id),
        "UnderlyingSeg": segment,
        "Expiry": expiry
    }
    data = safe_post(url, payload)

    # ---- DEBUG ----
    st.write("### Option Chain Raw Response")
    st.json(data)   # remove this after debugging
    # ---------------

    return data
