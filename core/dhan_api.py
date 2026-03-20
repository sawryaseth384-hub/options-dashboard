import requests
import streamlit as st

# 🔥 MUST ADD THIS
BASE_URL = "https://api.dhan.co/v2"


def get_headers():
    return {
        "access-token": st.secrets["ACCESS_TOKEN"],
        "client-id": st.secrets["CLIENT_ID"],
        "Content-Type": "application/json"
    }


# =========================
# 🔥 EXPIRY LIST
# =========================
def get_expiry_list(security_id, segment):
    try:
        url = f"{BASE_URL}/optionchain/expirylist"

        payload = {
            "UnderlyingScrip": security_id,
            "UnderlyingSeg": segment
        }

        res = requests.post(url, headers=get_headers(), json=payload)
        data = res.json()

        return data.get("data", [])

    except Exception as e:
        st.error(f"Expiry API Error: {e}")
        return []


# =========================
# 🔥 VALID EXPIRY
# =========================
def get_valid_expiries(security_id, segment):
    return get_expiry_list(security_id, segment)


# =========================
# 🔥 OPTION CHAIN
# =========================
def get_option_chain(security_id, segment, expiry):
    try:
        url = f"{BASE_URL}/optionchain"

        payload = {
            "UnderlyingScrip": security_id,
            "UnderlyingSeg": segment,
            "Expiry": expiry
        }

        res = requests.post(url, headers=get_headers(), json=payload)
        return res.json()

    except Exception as e:
        st.error(f"Option Chain Error: {e}")
        return None
