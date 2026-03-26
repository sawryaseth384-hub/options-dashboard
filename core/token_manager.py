import os
import streamlit as st


def _get_env_value(key):
    """Return a stripped environment variable value or an empty string."""
    value = os.getenv(key)
    return value.strip() if value else ""


def get_token():
    cached = st.session_state.get("token")
    if cached:
        return cached
    access_token = _get_env_value("DHAN_ACCESS_TOKEN")
    if access_token:
        st.session_state.token = access_token
        return access_token
    return None


def get_client_id():
    cached = st.session_state.get("client_id")
    if cached:
        return cached
    client_id = _get_env_value("DHAN_CLIENT_ID")
    if client_id:
        st.session_state.client_id = client_id
        return client_id
    return None


def get_headers():
    headers = {
        "Content-Type": "application/json"
    }
    token = get_token()
    client_id = get_client_id()
    if token:
        headers["access-token"] = token
    if client_id:
        headers["client-id"] = client_id
    return headers
