import requests
import streamlit as st

BASE_URL = "https://api.dhan.co/v2"

def get_headers():
    return {
        "access-token": st.secrets["ACCESS_TOKEN"],
        "client-id": st.secrets["CLIENT_ID"],
        "Content-Type": "application/json"
    }

def get_expiry(security_id, segment):

    url = f"{BASE_URL}/optionchain/expirylist"

    payload = {
        "UnderlyingScrip": int(security_id),
        "UnderlyingSeg": segment
    }

    try:
        res = requests.post(url, headers=get_headers(), json=payload, timeout=10)
        data = res.json()

        if not data or data.get("status") != "success":
            return []

        return data.get("data", [])

    except Exception as e:
        st.error(f"Expiry Error: {e}")
        return []
