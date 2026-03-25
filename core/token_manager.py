import requests
import pyotp
import streamlit as st

AUTH_URL = "https://auth.dhan.co/app/generateAccessToken"


def _get_secret(key):
    try:
        return st.secrets.get(key)
    except Exception:
        return None


def get_client_id():
    return _get_secret("CLIENT_ID") or _get_secret("client_id")


def get_token():
    try:
        if "token" in st.session_state:
            return st.session_state.token
    except Exception:
        pass

    static_token = _get_secret("ACCESS_TOKEN") or _get_secret("access_token")
    if static_token:
        try:
            st.session_state.token = static_token
        except Exception:
            pass
        return static_token

    totp_secret = _get_secret("TOTP_SECRET")
    client_id = get_client_id()
    pin = _get_secret("PIN")
    if not (totp_secret and client_id and pin):
        return None

    totp = pyotp.TOTP(totp_secret).now()
    payload = {"dhanClientId": client_id, "pin": pin, "totp": totp}

    try:
        res = requests.post(AUTH_URL, params=payload, timeout=10)
        data = res.json()
    except Exception:
        return None

    if "accessToken" in data:
        try:
            st.session_state.token = data["accessToken"]
        except Exception:
            pass
        return data["accessToken"]

    return None


def get_headers():
    token = get_token()
    client_id = get_client_id()
    if not token or not client_id:
        return None
    return {
        "access-token": token,
        "client-id": client_id,
        "Content-Type": "application/json",
    }
