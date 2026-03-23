# core/token_manager.py

import streamlit as st
import requests
import time
import pyotp
from datetime import datetime

AUTH_URL = "https://auth.dhan.co/app/generateAccessToken"

CLIENT_ID = st.secrets["CLIENT_ID"]
PIN = st.secrets["PIN"]
TOTP_SECRET = st.secrets["TOTP_SECRET"]

def get_headers():
    token = get_token()
    return {
        "access-token": token,
        "client-id": CLIENT_ID,
        "Content-Type": "application/json"
    }

def get_token():
    if "dhan_token" not in st.session_state:
        st.session_state.dhan_token = None
        st.session_state.token_expiry = 0

    if (
        st.session_state.dhan_token is None
        or time.time() > st.session_state.token_expiry
    ):
        _refresh_token()

    return st.session_state.dhan_token


def _refresh_token():
    try:
        totp = pyotp.TOTP(TOTP_SECRET).now()

        params = {
            "dhanClientId": CLIENT_ID,
            "pin": PIN,
            "totp": totp
        }

        resp = requests.post(AUTH_URL, params=params, timeout=10)

        print("RAW TOKEN RESPONSE:", resp.text)  # debug

        data = resp.json()

        if resp.status_code == 200 and "accessToken" in data:
            st.session_state.dhan_token = data["accessToken"]

            expiry_time = data.get("expiryTime")

            if expiry_time:
                expiry_dt = datetime.fromisoformat(expiry_time)
                st.session_state.token_expiry = expiry_dt.timestamp() - 60
            else:
                st.session_state.token_expiry = time.time() + 23 * 3600

        else:
            st.error(f"❌ Token failed: {data}")
            st.stop()

    except Exception as e:
        st.error(f"❌ Error: {e}")
        st.stop()
