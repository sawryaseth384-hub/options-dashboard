import logging
import os
import time

import pyotp
import requests
import streamlit as st

_logger = logging.getLogger(__name__)
_TOKEN_LOGGED = False
AUTH_URL = "https://auth.dhan.co/app/generateAccessToken"


def _get_secret_value(key):
    value = os.getenv(key)
    if value:
        return value.strip()
    try:
        secret_value = st.secrets.get(key)
    except Exception:
        secret_value = None
    return str(secret_value).strip() if secret_value else ""


def _mask_token(token):
    token = str(token or "")
    if len(token) <= 8:
        return "***"
    return f"{token[:4]}...{token[-4:]}"


def _log_token_once(token):
    global _TOKEN_LOGGED
    if _TOKEN_LOGGED:
        return
    _TOKEN_LOGGED = True
    _logger.info("Dhan access token loaded: %s", _mask_token(token))


def _extract_access_token(payload):
    if not isinstance(payload, dict):
        return None
    for key in ("accessToken", "access_token", "access-token", "token"):
        token = payload.get(key)
        if token:
            return token
    nested = payload.get("data") or payload.get("result")
    if isinstance(nested, dict):
        for key in ("accessToken", "access_token", "access-token", "token"):
            token = nested.get(key)
            if token:
                return token
    return None


def _generate_totp(secret):
    try:
        return pyotp.TOTP(secret).now()
    except Exception as exc:
        _logger.warning("TOTP generation failed: %s", exc)
        return None


def _request_access_token(client_id, pin, totp):
    if not client_id or not pin or not totp:
        return None, "Missing credentials for token generation"
    url = f"{AUTH_URL}?dhanClientId={client_id}&pin={pin}&totp={totp}"
    try:
        response = requests.post(url, timeout=10)
    except Exception as exc:
        return None, str(exc)
    if response.status_code != 200:
        return None, f"HTTP {response.status_code}"
    try:
        payload = response.json()
    except Exception as exc:
        return None, f"Invalid JSON response: {exc}"
    token = _extract_access_token(payload)
    if not token:
        return None, "Access token missing in response"
    return token, None


def get_token(force_refresh=False):
    cached = st.session_state.get("token")
    if cached and not force_refresh:
        return cached
    client_id = _get_secret_value("CLIENT_ID")
    pin = _get_secret_value("PIN")
    totp_secret = _get_secret_value("TOTP_SECRET")
    if not client_id or not pin or not totp_secret:
        _logger.warning("Missing CLIENT_ID, PIN, or TOTP_SECRET in secrets.")
        return None
    for attempt in range(1, 4):
        totp = _generate_totp(totp_secret)
        if not totp:
            return None
        token, error = _request_access_token(client_id, pin, totp)
        if token:
            st.session_state.token = token
            _log_token_once(token)
            return token
        _logger.warning("Token generation attempt %s failed: %s", attempt, error)
        if attempt < 3:
            time.sleep(0.5 * attempt)
    return None


def get_client_id():
    cached = st.session_state.get("client_id")
    if cached:
        return cached
    client_id = _get_secret_value("CLIENT_ID")
    if client_id:
        st.session_state.client_id = client_id
        return client_id
    return None


def clear_token():
    if "token" in st.session_state:
        del st.session_state["token"]


def get_headers():
    headers = {
        "Content-Type": "application/json"
    }
    token = get_token()
    if token:
        headers["access-token"] = token
    return headers
