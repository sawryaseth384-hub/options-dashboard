import os
import requests
import pyotp
import streamlit as st

AUTH_URL = "https://auth.dhan.co/app/generateAccessToken"


def _get_secret(key):
    if hasattr(st, "secrets") and key in st.secrets:
        return st.secrets.get(key)
    return os.getenv(key)


def get_client_id():
    return _get_secret("CLIENT_ID")

def get_token():

    # 🔒 अगर token already बना है → वही use करो
    if "token" in st.session_state:
        return st.session_state.token

    # ❌ नहीं है → सिर्फ 1 बार बनाओ
    totp_secret = _get_secret("TOTP_SECRET")
    client_id = get_client_id()
    pin = _get_secret("PIN")
    if not totp_secret or not client_id or not pin:
        st.error("Missing Dhan credentials in secrets or environment.")
        return None
    totp = pyotp.TOTP(totp_secret).now()

    payload = {
        "dhanClientId": client_id,
        "pin": pin,
        "totp": totp
    }

    res = requests.post(AUTH_URL, params=payload)
    data = res.json()

    if "accessToken" in data:
        st.session_state.token = data["accessToken"]
        return st.session_state.token

    st.error("Token Failed")
    return None


def get_headers():
    token = get_token()
    client_id = get_client_id()
    headers = {
        "Content-Type": "application/json"
    }
    if token:
        headers["access-token"] = token
    if client_id:
        headers["client-id"] = client_id
    return headers
