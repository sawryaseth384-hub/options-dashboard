import streamlit as st
import requests
import time
import pyotp
from datetime import datetime

AUTH_URL = "https://auth.dhan.co/app/generateAccessToken"

# =========================
# 🔐 GET TOKEN (MAIN)
# =========================
def get_token():

    # init session
    if "token" not in st.session_state:
        st.session_state.token = None
        st.session_state.expiry = 0

    # ✅ reuse token (valid for 24h)
    if st.session_state.token and time.time() < st.session_state.expiry:
        return st.session_state.token

    # 🔄 generate new token
    token, expiry = _generate_token()

    if token:
        st.session_state.token = token
        st.session_state.expiry = expiry
        return token

    return None


# =========================
# 🔄 FORCE REFRESH (IMPORTANT)
# =========================
def force_refresh_token():
    st.session_state.token = None
    st.session_state.expiry = 0


# =========================
# 🔑 GENERATE TOKEN
# =========================
def _generate_token():
    try:
        totp = pyotp.TOTP(st.secrets["TOTP_SECRET"])
        current_totp = totp.now()

        payload = {
            "dhanClientId": st.secrets["CLIENT_ID"],
            "pin": st.secrets["PIN"],
            "totp": current_totp
        }

        # 🔥 IMPORTANT: params use करना है
        res = requests.post(AUTH_URL, params=payload, timeout=10)

        if res.status_code != 200:
            st.error(f"❌ Token HTTP Error: {res.status_code}")
            return None, 0

        data = res.json()

        if "accessToken" not in data:
            st.error(f"❌ Token Failed: {data}")
            return None, 0

        # ✅ expiry handling
        expiry = data.get("expiryTime")

        if expiry:
            dt = datetime.fromisoformat(expiry)
            expiry_ts = dt.timestamp() - 60   # 1 min early refresh
        else:
            expiry_ts = time.time() + 23 * 3600

        st.success("✅ Token Generated")

        return data["accessToken"], expiry_ts

    except Exception as e:
        st.error(f"❌ Token Error: {e}")
        return None, 0


# =========================
# 📡 HEADERS
# =========================
def get_headers():
    token = get_token()

    return {
        "access-token": token,
        "client-id": st.secrets["CLIENT_ID"],
        "Content-Type": "application/json"
    }
