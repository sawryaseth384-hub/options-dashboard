import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from core.token_manager import get_headers
from dhan_data.expiry import get_expiry
from dhan_data.option_chain import get_option_chain

st.set_page_config(page_title="Dhan Options Dashboard", layout="wide")

st.title("📊 Dhan Options Dashboard")

# =========================
# Symbol
# =========================
symbol = st.text_input("Symbol", "NIFTY")
SECURITY_ID = 13

st.write(f"🔍 {symbol} security ID:", SECURITY_ID)

# =========================
# Expiry
# =========================
expiry_list = []

try:
    expiry_data = get_expiry(SECURITY_ID)
    st.write("📦 Expiry Raw:", expiry_data)

    if isinstance(expiry_data, list):
        expiry_list = expiry_data
    elif isinstance(expiry_data, dict) and "data" in expiry_data:
        expiry_list = expiry_data["data"]

except Exception as e:
    st.error(f"❌ Expiry Error: {e}")

if not expiry_list:
    st.warning("⚠️ No expiry found")
    st.stop()

expiry = st.selectbox("Select Expiry", expiry_list)

# =========================
# Option Chain
# =========================
st.subheader("📊 Option Chain")

try:
    option_data = get_option_chain(SECURITY_ID, expiry)
    st.write("📦 Raw API Response:", option_data)

    if option_data is None:
        st.error("❌ No response")

    elif isinstance(option_data, dict) and "error" in option_data:
        st.error(option_data["error"])

    elif isinstance(option_data, dict) and "data" in option_data:
        st.success("✅ Option Chain Loaded")
        st.json(option_data["data"])

    else:
        st.warning("⚠️ Unexpected format")
        st.write(option_data)

except Exception as e:
    st.error(f"❌ Option Error: {e}")
