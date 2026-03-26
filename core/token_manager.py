import os
import streamlit as st

DHAN_CLIENT_ID = os.getenv("DHAN_CLIENT_ID")
DHAN_ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN")


def get_token():
    cached = st.session_state.get("token")
    if cached:
        return cached
    if DHAN_ACCESS_TOKEN:
        st.session_state.token = DHAN_ACCESS_TOKEN
    return DHAN_ACCESS_TOKEN


def get_client_id():
    cached = st.session_state.get("client_id")
    if cached:
        return cached
    if DHAN_CLIENT_ID:
        st.session_state.client_id = DHAN_CLIENT_ID
    return DHAN_CLIENT_ID


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
