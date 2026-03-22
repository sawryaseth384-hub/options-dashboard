import pyotp
import streamlit as st

TOTP_SECRET = st.secrets["DJUQ7WLHTV2ZVFHOTOORRT3VGHQJCMLV"]

def get_totp():
    return pyotp.TOTP(TOTP_SECRET).now()
