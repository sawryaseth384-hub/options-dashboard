import requests
import time
import pyotp
from datetime import datetime
import streamlit as st

AUTH_URL = "https://auth.dhan.co/app/generateAccessToken"


# =========================
# GLOBAL TOKEN STORE (CLOUD SAFE)
# =========================
@st.cache_resource
def token_store():
    return {
        "token": None,
        "expiry": 0
    }


# =========================
# GET TOKEN (MAIN)
# =========================
def get_token():
    store = token_store()

    # ✅ अगर valid token है → reuse
    if store["token"] and time.time() < store["expiry"]:
        return store["token"]

    # ❌ Dhan restriction: 2 min block avoid
    if "last_call" in st.session_state:
        if time.time() - st.session_state.last_call < 120:
            return store["token"]

    # 🔁 नया token generate
    token, expiry = refresh_token()

    if token:
        store["token"] = token
        store["expiry"] = expiry
        st.session_state.last_call = time.time()
        return token

    return None


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

            # show only once
            if "token_shown" not in st.session_state:
                st.success("✅ Token Generated")
                st.session_state.token_shown = True

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

    if not token:
        raise Exception("❌ Token not available")

    return {
        "access-token": token,
        "client-id": st.secrets["CLIENT_ID"],
        "Content-Type": "application/json"
    }
