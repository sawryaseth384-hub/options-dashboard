import streamlit as st
import requests
import time
import pyotp
from datetime import datetime

AUTH_URL = "https://auth.dhan.co/app/generateAccessToken"


# =========================
# GET HEADERS
# =========================
def get_headers():
    token = get_token()
    return {
        "access-token": token,
        "client-id": st.secrets["CLIENT_ID"],
        "Content-Type": "application/json"
    }


# =========================
# GET TOKEN (SMART CACHE)
# =========================
def get_token():

    # session init
    if "token" not in st.session_state:
        st.session_state.token = None
        st.session_state.expiry = 0

    # ✅ reuse existing token (24h valid)
    if st.session_state.token and time.time() < st.session_state.expiry:
        return st.session_state.token

    # ❌ otherwise generate once
    token, expiry = refresh_token()

    if token:
        st.session_state.token = token
        st.session_state.expiry = expiry
        return token

    return None


# =========================
# REFRESH TOKEN (FIXED)
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

        # 🔥 IMPORTANT FIX: use params, not json
        res = requests.post(AUTH_URL, params=payload)

        data = res.json()

        if "accessToken" in data:

            expiry = data.get("expiryTime")

            if expiry:
                dt = datetime.fromisoformat(expiry)
                expiry_ts = dt.timestamp() - 60
            else:
                expiry_ts = time.time() + 23 * 3600

            st.success("✅ Token Generated (Once)")
            return data["accessToken"], expiry_ts

        else:
            st.error(f"❌ Token failed: {data}")
            return None, 0

    except Exception as e:
        st.error(f"❌ Token error: {e}")
        return None, 0
