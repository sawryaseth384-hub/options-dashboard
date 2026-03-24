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
        "client-id": st.secrets["CLIENT_ID"],
        "Content-Type": "application/json"
    }

def get_token():
    # Initialize session state if missing
    if "token" not in st.session_state:
        st.session_state.token = None
        st.session_state.expiry = 0
        st.session_state.last_call = 0

    # reuse valid token – ensure expiry is a number
    if st.session_state.token:
        try:
            expiry = float(st.session_state.expiry)
        except (TypeError, ValueError):
            expiry = 0
        if time.time() < expiry:
            return st.session_state.token

    # avoid calling token generation more than once every 120 seconds
    if time.time() - st.session_state.last_call < 120:
        return st.session_state.token

    return refresh_token()

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
            st.session_state.token = data["accessToken"]
            st.session_state.last_call = time.time()

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
        st.error(f"❌ Token Error: {e}")
        return None
