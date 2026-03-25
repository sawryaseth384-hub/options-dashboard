import streamlit as st
import requests
import time
import pyotp
from datetime import datetime

AUTH_URL = "https://auth.dhan.co/app/generateAccessToken"

# =========================
# GET TOKEN
# =========================
def get_token():

    if "token" not in st.session_state:
        st.session_state.token = None
        st.session_state.expiry = 0

    # ✅ reuse valid token
    if st.session_state.token and time.time() < st.session_state.expiry:
        return st.session_state.token

    # 🔄 generate new
    token, expiry = _generate_token()

    if token:
        st.session_state.token = token
        st.session_state.expiry = expiry
        return token

    return None


# =========================
# FORCE REFRESH
# =========================
def force_refresh_token():
    st.session_state.token = None
    st.session_state.expiry = 0


# =========================
# GENERATE TOKEN
# =========================
def _generate_token():
    try:
        totp = pyotp.TOTP(st.secrets["TOTP_SECRET"]).now()

        payload = {
            "dhanClientId": st.secrets["CLIENT_ID"],
            "pin": st.secrets["PIN"],
            "totp": totp
        }

        res = requests.post(AUTH_URL, params=payload, timeout=10)

        if res.status_code != 200:
            return None, 0

        data = res.json()

        if "accessToken" not in data:
            return None, 0

        expiry = data.get("expiryTime")

        if expiry:
            dt = datetime.fromisoformat(expiry)
            expiry_ts = dt.timestamp() - 60
        else:
            expiry_ts = time.time() + 23 * 3600

        return data["accessToken"], expiry_ts

    except:
        return None, 0


# =========================
# HEADERS
# =========================
def get_headers():
    return {
        "access-token": get_token(),
        "client-id": st.secrets["CLIENT_ID"],
        "Content-Type": "application/json"
    }
