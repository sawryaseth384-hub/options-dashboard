import requests
import streamlit as st
from datetime import datetime

BASE_URL = "https://api.dhan.co/v2"


# =========================
# 🔑 HEADERS
# =========================
def get_headers():
    return {
        "access-token": st.secrets["ACCESS_TOKEN"],
        "client-id": st.secrets["CLIENT_ID"],
        "Content-Type": "application/json"
    }


# =========================
# 🔥 EXPIRY LIST (DYNAMIC)
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

        if data.get("status") == "success":
            return data.get("data", [])

        return []

    except Exception as e:
        st.error(f"❌ Expiry API Error: {e}")
        return []


# =========================
# 🔥 FILTER EXPIRY (OPTIONAL)
# =========================
def get_valid_expiries(security_id, segment):
    expiries = get_expiry_list(security_id, segment)

    valid = []

    for exp in expiries:
        try:
            dt = datetime.strptime(exp, "%Y-%m-%d")

            # 👉 अभी ALL expiry allow कर रहे (safe)
            valid.append(exp)

            # 👉 अगर Tuesday filter चाहिए:
            # if dt.weekday() == 1:
            #     valid.append(exp)

        except:
            continue

    return valid


# =========================
# 🔥 OPTION CHAIN (DYNAMIC)
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
        data = res.json()

        return data

    except Exception as e:
        st.error(f"❌ Option Chain Error: {e}")
        return None
