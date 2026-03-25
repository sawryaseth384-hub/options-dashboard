import os
import time
import requests
import pyotp
import streamlit as st

AUTH_URL = "https://auth.dhan.co/app/generateAccessToken"

def _read_credential(key):
    try:
        secrets = st.secrets
        if key in secrets:
            return secrets[key]
    except (AttributeError, KeyError, TypeError, RuntimeError):
        pass
    return os.getenv(key)

def get_client_id():
    return _read_credential("CLIENT_ID") or _read_credential("DHAN_CLIENT_ID")

def get_token():

    access_token = _read_credential("ACCESS_TOKEN") or _read_credential("DHAN_ACCESS_TOKEN")
    if access_token:
        return access_token

    if "token" in st.session_state:
        return st.session_state.token

    totp_secret = _read_credential("TOTP_SECRET")
    pin = _read_credential("PIN")
    client_id = get_client_id()
    if not all([totp_secret, pin, client_id]):
        return None

    totp = pyotp.TOTP(totp_secret).now()

    payload = {
        "dhanClientId": client_id,
        "pin": pin,
        "totp": totp
    }

    try:
        res = requests.post(AUTH_URL, params=payload, timeout=10)
        data = res.json()
    except (requests.RequestException, ValueError):
        return None

    access_token = data.get("accessToken")
    if access_token:
        st.session_state.token = access_token
        return access_token

    return None

def get_headers():
    token = get_token()
    client_id = get_client_id()
    if not token or not client_id:
        return {}
    return {
        "access-token": token,
        "client-id": client_id,
        "Content-Type": "application/json"
    }
