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
    if "token" not in st.session_state:
        st.session_state.token = None
        st.session_state.expiry = 0

    if st.session_state.token is None or time.time() > st.session_state.expiry:
        refresh_token()

    return st.session_state.token

def refresh_token():
    try:
        # 🔥 TOTP generate
        totp = pyotp.TOTP(st.secrets["TOTP_SECRET"].strip())
        current_totp = totp.now()

        payload = {
            "dhanClientId": st.secrets["CLIENT_ID"],
            "pin": st.secrets["PIN"],
            "totp": current_totp
        }

        # 🔥 IMPORTANT → data (not params)
        res = requests.post(AUTH_URL, data=payload)

        print("RAW:", res.text)

        data = res.json()

        if res.status_code == 200 and "accessToken" in data:
            st.session_state.token = data["accessToken"]

            expiry = data.get("expiryTime")
            if expiry:
                dt = datetime.fromisoformat(expiry)
                st.session_state.expiry = dt.timestamp() - 60
            else:
                st.session_state.expiry = time.time() + 23 * 3600

            st.success("✅ Token Generated")

        else:
            st.error(f"❌ Token Failed: {data}")
            st.stop()

    except Exception as e:
        st.error(f"❌ Error: {e}")
        st.stop()
