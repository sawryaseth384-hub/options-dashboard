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
    try:
        url = f"{BASE_URL}/optionchain/expirylist"

        payload = {
            "UnderlyingScrip": int(security_id),
            "UnderlyingSeg": segment
        }

        res = requests.post(
            url,
            headers=get_headers(),
            json=payload,
            timeout=10
        )

        data = res.json()

        # ✅ IMPORTANT FIX
        if data.get("status") != "success":
            return []

        expiry_list = data.get("data", [])

        # ensure list
        if isinstance(expiry_list, list):
            return expiry_list

        return []

    except Exception as e:
        print("Expiry Error:", e)
        return []
