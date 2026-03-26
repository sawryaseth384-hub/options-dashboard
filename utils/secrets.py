import os


def get_secret(key, default=None):
    env_value = os.getenv(key, default)
    try:
        import streamlit as st

        value = st.secrets.get(key, None)
        if value is None:
            return env_value
        if isinstance(value, str) and not value.strip():
            return env_value
        return value
    except Exception:
        return env_value
