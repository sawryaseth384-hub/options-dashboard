import requests
import time
import json
import os
import pyotp
from datetime import datetime
import streamlit as st

AUTH_URL = "https://auth.dhan.co/app/generateAccessToken"
TOKEN_FILE = "token.json"


# =========================
# SAVE TOKEN
# =========================
def save_token(token, expiry):
    with open(TOKEN_FILE, "w") as f:
        json.dump({
            "token": token,
            "expiry": expiry
        }, f)


# =========================
# LOAD TOKEN
# =========================
def load_token():
    if not os.path.exists(TOKEN_FILE):
        return None, 0

    try:
        with open(TOKEN_FILE, "r") as f:
            data = json.load(f)
            return data.get("token"), data.get("expiry", 0)
    except:
        return None, 0


# =========================
# GET TOKEN
# =========================
def get_token():
    token, expiry = load_token()

    # ✅ valid token → reuse
    if token and time.time() < expiry:
        return token

    # 🔁 generate new token
    token, expiry = refresh_token()

    if token:
        save_token(token, expiry)
        return token

    raise Exception("❌ Unable to get token")


# =========================
# REFRESH TOKEN
# =========================
def refresh_token():
    try:
        totp = pyotp.TOTP(st.secrets["TOTP_SECRET"])
        current_totp = totp.now()

        payload = {
            "dhanClientId": st.secrets["CLIENT_ID"],
            "pin": st.secrets["PIN"],
            "totp": current_totp
        }

        res = requests.post(AUTH_URL, json=payload, timeout=10)
        data = res.json()

        if "accessToken" in data:

            expiry = data.get("expiryTime")

            if expiry:
                dt = datetime.fromisoformat(expiry)
                expiry_ts = dt.timestamp() - 60
            else:
                expiry_ts = time.time() + 23 * 3600

            st.success("✅ New Token Generated")

            return data["accessToken"], expiry_ts

        else:
            st.error(f"❌ Token failed: {data}")
            return None, 0

    except Exception as e:
        st.error(f"❌ Token error: {e}")
        return None, 0


# =========================
# HEADERS
# =========================
def get_headers():
    token = get_token()

    return {
        "access-token": token,
        "client-id": st.secrets["CLIENT_ID"],
        "Content-Type": "application/json"
    }
