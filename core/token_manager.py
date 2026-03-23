import streamlit as st
import requests
import time
import pyotp
from datetime import datetime

AUTH_URL = "https://auth.dhan.co/app/generateAccessToken"

def get_headers():
    token = get_token()
    return {
        "access-token": token,
        "client-id": st.secrets["CLIENT_ID"],   # ✅ FIXED
        "Content-Type": "application/json"
    }
def get_token():
    if "token" not in st.session_state:
        st.session_state.token = None
        st.session_state.expiry = 0
        st.session_state.last_token_time = 0

    # ✅ reuse existing token
    if st.session_state.token and time.time() < st.session_state.expiry:
        return st.session_state.token

    return refresh_token()

def refresh_token():
    try:
        # 🛑 Rate limit fix
        if time.time() - st.session_state.last_token_time < 120:
            return st.session_state.token

        totp = pyotp.TOTP(st.secrets["TOTP_SECRET"])
        current_totp = totp.now()

        payload = {
            "dhanClientId": st.secrets["CLIENT_ID"],
            "pin": st.secrets["PIN"],
            "totp": current_totp
        }

        res = requests.post(AUTH_URL, data=payload)
        data = res.json()

        if res.status_code == 200 and "accessToken" in data:
            st.session_state.token = data["accessToken"]
            st.session_state.last_token_time = time.time()

            expiry = data.get("expiryTime")
            if expiry:
                dt = datetime.fromisoformat(expiry)
                st.session_state.expiry = dt.timestamp() - 60
            else:
                st.session_state.expiry = time.time() + 23 * 3600

            st.success("✅ Token Generated")

            return st.session_state.token

        else:
            st.error(f"❌ Token failed: {data}")
            return None

    except Exception as e:
        st.error(f"❌ Error: {e}")
        return None
