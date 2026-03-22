import requests
import time
import streamlit as st
from core.totp import get_totp

CLIENT_ID = st.secrets["1106299230"]
PIN = st.secrets["009988"]

TOKEN_URL = "https://auth.dhan.co/app/generateAccessToken"

token_cache = {
    "token": None,
    "expiry": 0
}

def generate_token():
    try:
        totp = get_totp()

        res = requests.post(
            TOKEN_URL,
            params={
                "dhanClientId": CLIENT_ID,
                "pin": PIN,
                "totp": totp
            },
            timeout=10
        )

        data = res.json()

        if "accessToken" in data:
            token_cache["token"] = data["accessToken"]
            token_cache["expiry"] = time.time() + (23 * 60 * 60)
            return token_cache["token"]
        else:
            print("❌ Token Error:", data)
            return None

    except Exception as e:
        print("❌ Token Exception:", e)
        return None


def get_token():
    if token_cache["token"] is None or time.time() > token_cache["expiry"]:
        return generate_token()
    return token_cache["token"]


def get_headers():
    token = get_token()
    return {
        "access-token": token,
        "client-id": CLIENT_ID,
        "Content-Type": "application/json"
    }
