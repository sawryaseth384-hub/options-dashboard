import requests
import pyotp
import time
import streamlit as st

AUTH_URL = "https://auth.dhan.co/app/generateAccessToken"


def _get_secret(key):
    try:
        return st.secrets.get(key)
    except Exception:
        return None


def get_token():
    cached = st.session_state.get("token")
    if cached:
        return cached

    access_token = _get_secret("ACCESS_TOKEN")
    if access_token:
        st.session_state.token = access_token
        return access_token

    try:
        totp_secret = _get_secret("TOTP_SECRET")
        client_id = _get_secret("CLIENT_ID")
        pin = _get_secret("PIN")
        if not all([totp_secret, client_id, pin]):
            return None

        totp = pyotp.TOTP(totp_secret).now()
        payload = {
            "dhanClientId": client_id,
            "pin": pin,
            "totp": totp,
        }
        res = requests.post(AUTH_URL, params=payload, timeout=10)
        data = res.json()
    except Exception:
        return None

    token = data.get("accessToken") if isinstance(data, dict) else None
    if token:
        st.session_state.token = token
        return token
    return None


def get_headers():
    token = get_token()
    client_id = _get_secret("CLIENT_ID")
    if not token or not client_id:
        return {}
    return {
        "access-token": token,
        "client-id": client_id,
        "Content-Type": "application/json",
    }
