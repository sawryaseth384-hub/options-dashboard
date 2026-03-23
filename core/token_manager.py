import streamlit as st
import requests
import time
import pyotp
from datetime import datetime

AUTH_URL = "https://auth.dhan.co/app/generateAccessToken"

def get_headers():
    token = get_token()
    return {
        "access-token": token,
        "client-id": st.secrets["CLIENT_ID"],
        "Content-Type": "application/json"
    }

def get_token():
    if "token" not in st.session_state:
        st.session_state.token = None
        st.session_state.expiry = 0
        st.session_state.last_call = 0
        st.session_state.generated_at = None   # 🆕 add

    # ✅ reuse token
    if st.session_state.token and time.time() < st.session_state.expiry:
        show_token_status()   # 🆕 show info
        return st.session_state.token

    return refresh_token()

def refresh_token():
    try:
        # 🔥 rate limit fix
        if time.time() - st.session_state.last_call < 120:
            show_token_status()
            return st.session_state.token

        totp = pyotp.TOTP(st.secrets["TOTP_SECRET"])
        current_totp = totp.now()

        payload = {
            "dhanClientId": st.secrets["CLIENT_ID"],
            "pin": st.secrets["PIN"],
            "totp": current_totp
        }

        res = requests.post(AUTH_URL, data=payload)
        data = res.json()

        if "accessToken" in data:
            st.session_state.token = data["accessToken"]
            st.session_state.last_call = time.time()

            # 🆕 store generation time
            st.session_state.generated_at = datetime.now()

            expiry = data.get("expiryTime")
            if expiry:
                dt = datetime.fromisoformat(expiry)
                st.session_state.expiry = dt.timestamp() - 60
            else:
                st.session_state.expiry = time.time() + 23 * 3600

            st.success("✅ Token Generated")

            show_token_status()  # 🆕 show info

            return st.session_state.token

        else:
            st.error(f"❌ Token failed: {data}")
            return None

    except Exception as e:
        st.error(f"❌ Token Error: {e}")
        return None


# 🔥 NEW FUNCTION (IMPORTANT)
def show_token_status():
    if st.session_state.generated_at:
        gen_time = st.session_state.generated_at.strftime("%H:%M:%S")
        expiry_time = datetime.fromtimestamp(st.session_state.expiry).strftime("%H:%M:%S")

        remaining = int(st.session_state.expiry - time.time())
        minutes = remaining // 60

        st.info(f"""
🕒 Token Generated: {gen_time}  
⏳ Expires At: {expiry_time}  
⌛ Remaining: {minutes} min
""")
