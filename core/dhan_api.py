import requests
import streamlit as st
from core.token_manager import get_token

CLIENT_ID = st.secrets["1106299230"]

BASE_URL = "https://api.dhan.co/v2"

def get_headers():
    return {
        "access-token": get_token(),
        "client-id": CLIENT_ID,
        "Content-Type": "application/json"
    }


def get_option_chain():
    url = f"{BASE_URL}/optionchain"

    payload = {
        "UnderlyingScrip": 13,
        "UnderlyingSeg": "IDX_I",
        "Expiry": "2026-03-24"
    }

    res = requests.post(url, headers=get_headers(), json=payload)

    return res.json()
