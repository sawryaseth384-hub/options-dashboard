import pyotp
import streamlit as st

TOTP_SECRET = st.secrets["TOTP_SECRET"]

def get_totp():
    return pyotp.TOTP(TOTP_SECRET).now()
