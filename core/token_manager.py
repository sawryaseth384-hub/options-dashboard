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
        "client-id": st.secrets["1106299230"],
        "Content-Type": "application/json"
    }

def get_token():
    # 🔥 Already token hai → reuse karo
    if "token" in st.session_state and time.time() < st.session_state.get("expiry", 0):
        return st.session_state.token

    # 🔥 warna naya generate karo
    return refresh_token()

def refresh_token():
    try:
        # 🛑 RATE LIMIT PROTECTION
        last_gen = st.session_state.get("last_token_time", 0)
        if time.time() - last_gen < 120:
            st.warning("⏳ Wait 2 min before generating new token")
            return st.session_state.get("token", None)

        totp = pyotp.TOTP(st.secrets["TOTP_SECRET"].strip()).now()

        payload = {
            "dhanClientId": st.secrets["CLIENT_ID"],
            "pin": st.secrets["PIN"],
            "totp": totp
        }

        res = requests.post(AUTH_URL, data=payload)

        data = res.json()

        if res.status_code == 200 and "accessToken" in data:
            token = data["accessToken"]

            st.session_state.token = token
            st.session_state.last_token_time = time.time()

            expiry = data.get("expiryTime")
            if expiry:
                dt = datetime.fromisoformat(expiry)
                st.session_state.expiry = dt.timestamp() - 60
            else:
                st.session_state.expiry = time.time() + 23 * 3600

            st.success("✅ Token Generated")

            return token

        else:
            st.error(f"❌ Token Failed: {data}")
            return None

    except Exception as e:
        st.error(f"❌ Error: {e}")
        return None
