import streamlit as st
import requests
import time
import pyotp
from datetime import datetime

AUTH_URL = "https://auth.dhan.co/app/generateAccessToken"

CLIENT_ID = st.secrets["1106299230"]
PIN = st.secrets["210519"]
TOTP_SECRET = st.secrets["EKPFBVGOSXOYOU42T53D2Q5SBHY3WUHS"]

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

    if st.session_state.dhan_token is None or time.time() > st.session_state.token_expiry:
        _refresh_token()

    return st.session_state.dhan_token

def _refresh_token():
    try:
        # 🔥 Generate TOTP
        totp = pyotp.TOTP(TOTP_SECRET.strip())
        current_totp = totp.now()

        payload = {
            "dhanClientId": CLIENT_ID,
            "pin": PIN,
            "totp": current_totp
        }

        # 🔥 IMPORTANT FIX → data= (NOT params)
        resp = requests.post(AUTH_URL, data=payload)

        print("STATUS:", resp.status_code)
        print("RAW:", resp.text)

        data = resp.json()

        if resp.status_code == 200 and "accessToken" in data:
            st.session_state.dhan_token = data["accessToken"]

            expiry_time = data.get("expiryTime")
            if expiry_time:
                expiry_dt = datetime.fromisoformat(expiry_time)
                st.session_state.token_expiry = expiry_dt.timestamp() - 60
            else:
                st.session_state.token_expiry = time.time() + (23 * 60 * 60)

            st.success("✅ Token Generated Successfully")

        else:
            st.error(f"❌ Token failed: {data}")
            st.stop()

    except Exception as e:
        st.error(f"❌ Error refreshing token: {e}")
        st.stop()
