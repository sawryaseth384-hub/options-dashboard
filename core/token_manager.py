import streamlit as st
import requests
import time
import pyotp
from datetime import datetime

AUTH_URL = "https://auth.dhan.co/app/generateAccessToken"


# 🔥 GLOBAL STORE (token save रहेगा)
@st.cache_resource
def token_store():
    return {"token": None, "expiry": 0}


# =========================
# GET TOKEN
# =========================
def get_token():
    store = token_store()

    # ✅ अगर token है और valid है → वही use
    if store["token"] and time.time() < store["expiry"]:
        return store["token"]

    # ❌ नहीं है / expire हो गया → नया बनाओ
    token, expiry = refresh_token()

    if token:
        store["token"] = token
        store["expiry"] = expiry
        return token

    return None


# =========================
# REFRESH TOKEN
# =========================
def refresh_token():
    try:
        totp = pyotp.TOTP(st.secrets["TOTP_SECRET"])
        current_totp = totp.now()

        payload = {
            "dhanClientId": st.secrets["CLIENT_ID"],
            "pin": st.secrets["PIN"],
            "totp": current_totp
        }

        res = requests.post(AUTH_URL, params=payload)
        data = res.json()

        if "accessToken" in data:

            # 👉 अगर expiry API दे रही है
            expiry = data.get("expiryTime")

            if expiry:
                dt = datetime.fromisoformat(expiry)
                expiry_ts = dt.timestamp()
            else:
                # 👉 default 24 घंटे
                expiry_ts = time.time() + 24 * 3600

            return data["accessToken"], expiry_ts

        return None, 0

    except Exception as e:
        st.error(e)
        return None, 0


# =========================
# HEADERS
# =========================
def get_headers():
    token = get_token()
    return {
        "access-token": token,
        "client-id": st.secrets["CLIENT_ID"],
        "Content-Type": "application/json"
    }
