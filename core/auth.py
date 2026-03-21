import requests
import pyotp
import streamlit as st
import time

# =========================
# 🔐 CONFIG (from secrets)
# =========================
CLIENT_ID = st.secrets["1106299230"]
PIN = st.secrets["009988"]
TOTP_SECRET = st.secrets["TOTP_SECRET"]

# =========================
# 🔥 GENERATE ACCESS TOKEN
# =========================
def generate_token():
    try:
        # 🔑 Generate TOTP (हर 30 sec नया)
        totp = pyotp.TOTP(TOTP_SECRET).now()

        url = f"https://auth.dhan.co/app/generateAccessToken?dhanClientId={CLIENT_ID}&pin={PIN}&totp={totp}"

        res = requests.post(url, timeout=10)
        data = res.json()

        # ✅ SUCCESS
        if "accessToken" in data:
            return data["accessToken"]

        # ❌ ERROR
        st.error(f"❌ Token Error: {data}")
        return None

    except Exception as e:
        st.error(f"❌ Token Exception: {e}")
        return None


# =========================
# ⚡ AUTO TOKEN CACHE
# =========================
@st.cache_resource(ttl=86400)  # 24 hours
def get_token():
    return generate_token()


# =========================
# 🔄 FORCE REFRESH TOKEN
# =========================
def refresh_token():
    get_token.clear()
    return get_token()
