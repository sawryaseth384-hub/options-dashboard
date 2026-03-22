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
        res = requests.post(
            TOKEN_URL,
            params={
                "dhanClientId": CLIENT_ID,
                "pin": PIN,
                "totp": get_totp()
            },
            timeout=10
        )

        data = res.json()

        if "accessToken" in data:
            token_cache["token"] = data["accessToken"]

            from datetime import datetime
            expiry = datetime.fromisoformat(data["expiryTime"]).timestamp()

            token_cache["expiry"] = expiry - 60

            return token_cache["token"]

        else:
            print("Token Error:", data)
            return None

    except Exception as e:
        print("Token Exception:", e)
        return None


def get_token():
    if token_cache["token"] is None or time.time() > token_cache["expiry"]:
        return generate_token()

    return token_cache["token"]
