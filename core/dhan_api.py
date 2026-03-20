import requests
import streamlit as st
import time

BASE_URL = "https://api.dhan.co/v2"

def get_headers():
    return {
        "access-token": st.secrets["ACCESS_TOKEN"],
        "client-id": st.secrets["CLIENT_ID"],
        "Content-Type": "application/json"
    }

@st.cache_data(ttl=300)
def get_expiry_list():
    try:
        url = f"{BASE_URL}/optionchain/expirylist"
        payload = {
            "UnderlyingScrip": 13,
            "UnderlyingSeg": "IDX_I"
        }

        res = requests.post(url, headers=get_headers(), json=payload)
        data = res.json()

        if data.get("status") == "success":
            return data.get("data", [])
        return []

    except Exception as e:
        st.error(f"Expiry API Error: {e}")
        return []

@st.cache_data(ttl=5)
def get_option_chain(expiry):
    try:
        url = f"{BASE_URL}/optionchain"
        payload = {
            "UnderlyingScrip": 13,
            "UnderlyingSeg": "IDX_I",
            "Expiry": expiry
        }

        res = requests.post(url, headers=get_headers(), json=payload)
        return res.json()

    except Exception as e:
        st.error(f"Option Chain Error: {e}")
        return None

@st.cache_data(ttl=300)
def get_valid_expiries():
    expiries = get_expiry_list()
    valid = []

    for exp in expiries[:3]:
        data = get_option_chain(exp)

        if data and data.get("status") == "success":
            valid.append(exp)

        time.sleep(3)

    return valid
