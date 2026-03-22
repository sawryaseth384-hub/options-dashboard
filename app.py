import streamlit as st
from core.token_manager import get_headers
import requests

st.title("🔥 Dhan API Test")

if st.button("Test Token"):
    headers = get_headers()
    st.write(headers)

    # Test API (profile)
    url = "https://api.dhan.co/v2/profile"
    res = requests.get(url, headers=headers)

    st.write(res.json())
