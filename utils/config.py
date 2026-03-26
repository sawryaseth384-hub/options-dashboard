import streamlit as st


def get_keys():
    return {
        "CLIENT_ID": st.secrets.get("CLIENT_ID"),
        "PIN": st.secrets.get("PIN"),
        "TOTP_SECRET": st.secrets.get("TOTP_SECRET"),
    }
