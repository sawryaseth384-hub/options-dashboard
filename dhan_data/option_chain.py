import requests
import streamlit as st
import time

BASE_URL = "https://api.dhan.co/v2"

_last_call_time = 0


# =========================
# 🔐 HEADERS
# =========================
def get_headers():
    return {
        "access-token": st.secrets["ACCESS_TOKEN"],
        "client-id": st.secrets["CLIENT_ID"],
        "Content-Type": "application/json"
    }


# =========================
# ⚡ SAFE POST
# =========================
def safe_post(url, payload, retries=2):
    global _last_call_time

    for attempt in range(retries):
        now = time.time()
        wait = max(0, 1 - (now - _last_call_time))  # 🔥 1 sec enough
        if wait > 0:
            time.sleep(wait)

        try:
            res = requests.post(
                url,
                headers=get_headers(),
                json=payload,
                timeout=10
            )

            _last_call_time = time.time()
            data = res.json()

            if not data:
                return None

            # ❌ failure case
            if data.get("status") == "failure":
                return None

            return data

        except Exception:
            continue

    return None


# =========================
# 📅 EXPIRY LIST
# =========================
def get_expiry_list(security_id, segment):

    url = f"{BASE_URL}/optionchain/expirylist"

    payload = {
        "UnderlyingScrip": int(security_id),
        "UnderlyingSeg": segment
    }

    data = safe_post(url, payload)

    if not data or data.get("status") != "success":
        return []

    return data.get("data", [])


# =========================
# 📊 OPTION CHAIN
# =========================
def get_option_chain(security_id, segment, expiry=None):

    # 🔥 get expiry if not given
    if not expiry:
        expiries = get_expiry_list(security_id, segment)

        if not expiries:
            return None

        expiry = sorted(expiries)[0]

    url = f"{BASE_URL}/optionchain"

    payload = {
        "UnderlyingScrip": int(security_id),
        "UnderlyingSeg": segment,
        "Expiry": expiry
    }

    data = safe_post(url, payload)

    return data
