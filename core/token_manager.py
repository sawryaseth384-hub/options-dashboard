import requests
import pyotp
import streamlit as st

AUTH_URL = "https://auth.dhan.co/app/generateAccessToken"

def get_token():

    # 🔒 अगर token already बना है → वही use करो
    if "token" in st.session_state:
        return st.session_state.token

    # ❌ नहीं है → सिर्फ 1 बार बनाओ
    totp = pyotp.TOTP(st.secrets["TOTP_SECRET"]).now()

    payload = {
        "dhanClientId": st.secrets["CLIENT_ID"],
        "pin": st.secrets["PIN"],
        "totp": totp
    }

    res = requests.post(AUTH_URL, params=payload)
    data = res.json()

    if "accessToken" in data:
        st.session_state.token = data["accessToken"]
        return st.session_state.token

    st.error("Token Failed")
    return None


def get_headers():
    token = get_token()
    client_id = st.secrets.get("CLIENT_ID")
    if not token or not client_id:
        raise RuntimeError("Missing Dhan credentials.")
    return {
        "access-token": token,
        "client-id": client_id,
        "Content-Type": "application/json",
    }
