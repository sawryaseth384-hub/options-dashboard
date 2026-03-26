import os


def get_secret(key, default=None):
    try:
        import streamlit as st

        return st.secrets.get(key, os.getenv(key, default))
    except Exception:
        return os.getenv(key, default)
