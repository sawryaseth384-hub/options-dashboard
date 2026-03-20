import requests
import streamlit as st
from datetime import datetime

BASE_URL = "https://api.dhan.co/v2"


def get_headers():
    return {
        "access-token": st.secrets["ACCESS_TOKEN"],
        "client-id": st.secrets["CLIENT_ID"],
        "Content-Type": "application/json"
    }


# ✅ EXPIRY LIST
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


# ✅ FILTER ONLY TUESDAY
def get_valid_expiries():
    expiries = get_expiry_list()
    valid = []

    for exp in expiries:
        try:
            dt = datetime.strptime(exp, "%Y-%m-%d")

            if dt.weekday() == 1:  # Tuesday
                valid.append(exp)

        except:
            continue

    return valid


# ✅ OPTION CHAIN
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
