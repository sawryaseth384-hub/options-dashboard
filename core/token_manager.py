import os
import logging
import streamlit as st

_logger = logging.getLogger(__name__)
_TOKEN_LOGGED = False


def _get_env_value(key):
    """Return a stripped environment or Streamlit secret value, or an empty string."""
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


def get_token():
    cached = st.session_state.get("token")
    if cached:
        return cached
    access_token = _get_env_value("DHAN_ACCESS_TOKEN") or _get_env_value("ACCESS_TOKEN")
    if access_token:
        st.session_state.token = access_token
        _log_token_once(access_token)
        return access_token
    return None


def get_client_id():
    cached = st.session_state.get("client_id")
    if cached:
        return cached
    client_id = _get_env_value("DHAN_CLIENT_ID") or _get_env_value("CLIENT_ID")
    if client_id:
        st.session_state.client_id = client_id
        return client_id
    return None


def get_headers():
    headers = {
        "Content-Type": "application/json"
    }
    token = get_token()
    if token:
        headers["access-token"] = token
    return headers
