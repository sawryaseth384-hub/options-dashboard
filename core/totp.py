import pyotp
import streamlit as st

# ✅ Correct (key name use करो)
TOTP_SECRET = st.secrets["DJUQ7WLHTV2ZVFHOTOORRT3VGHQJCMLV"]

def get_totp():
    return pyotp.TOTP(TOTP_SECRET).now()
