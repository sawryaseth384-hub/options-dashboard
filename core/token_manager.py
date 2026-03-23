import streamlit as st
import requests
from core.totp import get_totp

# ✅ Correct keys from secrets
CLIENT_ID = st.secrets["1106299230"]
PIN = st.secrets["009988"]

def generate_token():
    url = "https://auth.dhan.co/app/generateAccessToken"

    res = requests.post(
        url,
        params={
            "dhanClientId": CLIENT_ID,
            "pin": PIN,
            "totp": get_totp()
        }
    )

    data = res.json()

    if "accessToken" in data:
        return data["accessToken"]
    else:
        st.error(f"Token Error: {data}")
        return None


def get_headers():
    token = generate_token()

    return {
        "access-token": token,
        "client-id": CLIENT_ID,
        "Content-Type": "application/json"
    }
