import pyotp
import streamlit as st

def get_totp():
    try:
        # ✅ Get secret from Streamlit secrets
        totp_secret = st.secrets["DJUQ7WLHTV2ZVFHOTOORRT3VGHQJCMLV"]

        # ✅ Generate TOTP
        return pyotp.TOTP(totp_secret).now()

    except KeyError:
        st.error("❌ TOTP_SECRET missing in Streamlit secrets")
        return None

    except Exception as e:
        st.error(f"❌ TOTP Error: {e}")
        return None
