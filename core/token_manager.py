# core/token_manager.py
import streamlit as st
import requests
import time
import pyotp

AUTH_URL = "https://auth.dhan.co/app/generateAccessToken"

# Use secrets for credentials
CLIENT_ID = st.secrets["1106299230"]
PIN = st.secrets["009988"]
TOTP_SECRET = st.secrets["DJUQ7WLHTV2ZVFHOTOORRT3VGHQJCMLV"]

def get_headers():
    """Return headers with a valid access token (auto‑refreshed)."""
    token = get_token()
    return {
        "access-token": token,
        "client-id": CLIENT_ID,
        "Content-Type": "application/json"
    }

def get_token():
    """Return a valid access token, refreshing if necessary."""
    # Use session state to store token and expiry across reruns
    if "dhan_token" not in st.session_state:
        st.session_state.dhan_token = None
        st.session_state.token_expiry = 0

    if st.session_state.dhan_token is None or time.time() > st.session_state.token_expiry:
        _refresh_token()

    return st.session_state.dhan_token

def _refresh_token():
    """Generate a fresh token using PIN and TOTP."""
    try:
        # Generate current TOTP code
        totp = pyotp.TOTP(TOTP_SECRET)
        current_totp = totp.now()

        params = {
            "dhanClientId": CLIENT_ID,
            "pin": PIN,
            "totp": current_totp
        }
        resp = requests.post(AUTH_URL, params=params, timeout=10)
        data = resp.json()

        if resp.status_code == 200 and "accessToken" in data:
            st.session_state.dhan_token = data["accessToken"]

            # Use API expiry time if available, otherwise default 24h
            expiry_time = data.get("expiryTime")
            if expiry_time:
                from datetime import datetime
                expiry_dt = datetime.fromisoformat(expiry_time)
                st.session_state.token_expiry = expiry_dt.timestamp() - 60  # buffer 1 min
            else:
                st.session_state.token_expiry = time.time() + (23 * 60 * 60)  # 23h as fallback
        else:
            st.error(f"Token refresh failed: {data}")
            st.stop()
    except Exception as e:
        st.error(f"Error refreshing token: {e}")
        st.stop()
