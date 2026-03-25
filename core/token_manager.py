import requests
import pyotp
import time
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
