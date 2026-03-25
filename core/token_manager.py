import streamlit as st
import requests
import pyotp
import time
from datetime import datetime

AUTH_URL = "https://auth.dhan.co/app/generateAccessToken"

def get_token():

    if "token" not in st.session_state:
        st.session_state.token = None
        st.session_state.expiry = 0

    # ✅ reuse token (24h)
    if st.session_state.token and time.time() < st.session_state.expiry:
        return st.session_state.token

    try:
        totp = pyotp.TOTP(st.secrets["TOTP_SECRET"]).now()

        payload = {
            "dhanClientId": st.secrets["CLIENT_ID"],
            "pin": st.secrets["PIN"],
            "totp": totp
        }

        res = requests.post(AUTH_URL, params=payload)
        data = res.json()

        if "accessToken" in data:
            expiry = data.get("expiryTime")

            if expiry:
                dt = datetime.fromisoformat(expiry)
                expiry_ts = dt.timestamp() - 60
            else:
                expiry_ts = time.time() + 23 * 3600

            st.session_state.token = data["accessToken"]
            st.session_state.expiry = expiry_ts

            return data["accessToken"]

        return None

    except Exception as e:
        st.error(f"Token Error: {e}")
        return None
