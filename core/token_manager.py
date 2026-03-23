# core/token_manager.py

import streamlit as st
import requests
import time
import pyotp
from datetime import datetime

AUTH_URL = "https://auth.dhan.co/app/generateAccessToken"

# 🔐 Secrets (Streamlit se)
CLIENT_ID = st.secrets["1106299230"]
PIN = st.secrets["210519"]
TOTP_SECRET = st.secrets["EKPFBVGOSXOYOU42T53D2Q5SBHY3WUHS"]

# =========================
# 🔹 Get Headers (API use)
# =========================
def get_headers():
    token = get_token()
    return {
        "access-token": token,
        "client-id": CLIENT_ID,
        "Content-Type": "application/json"
    }

# =========================
# 🔹 Get Token (Auto refresh)
# =========================
def get_token():
    if "dhan_token" not in st.session_state:
        st.session_state.dhan_token = None
        st.session_state.token_expiry = 0

    # 🔥 Token expired ya nahi
    if (
        st.session_state.dhan_token is None
        or time.time() > st.session_state.token_expiry
    ):
        _refresh_token()

    return st.session_state.dhan_token

# =========================
# 🔹 Refresh Token (MAIN)
# =========================
def _refresh_token():
    try:
        # 🔥 TOTP generate
        totp = pyotp.TOTP(TOTP_SECRET.strip())
        current_totp = totp.now()

        # 🔍 Debug (optional)
        print("Generated TOTP:", current_totp)

        params = {
            "dhanClientId": CLIENT_ID,
            "pin": PIN,
            "totp": current_totp
        }

        # 🔥 IMPORTANT FIX → data= (not params=)
        resp = requests.post(AUTH_URL, data=params, timeout=10)

        print("Status:", resp.status_code)
        print("Raw:", resp.text)

        data = resp.json()

        # ✅ Success
        if resp.status_code == 200 and "accessToken" in data:
            st.session_state.dhan_token = data["accessToken"]

            expiry_time = data.get("expiryTime")

            if expiry_time:
                expiry_dt = datetime.fromisoformat(expiry_time)
                # 🔥 1 min pehle refresh
                st.session_state.token_expiry = expiry_dt.timestamp() - 60
            else:
                st.session_state.token_expiry = time.time() + 23 * 3600

            st.success("✅ Token Generated")

        else:
            st.error(f"❌ Token failed: {data}")
            st.stop()

    except Exception as e:
        st.error(f"❌ Error: {e}")
        st.stop()
