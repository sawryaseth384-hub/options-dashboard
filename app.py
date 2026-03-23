import streamlit as st
from core.token_manager import get_headers
from expiry import get_expiry
from option_chain import get_option_chain

st.title("📊 Dhan Options Dashboard")

symbol = st.text_input("Symbol", "NIFTY")

# ✅ fixed ID
SECURITY_ID = 13

st.write("🔍 NIFTY security ID:", SECURITY_ID)

# 🔥 Step 1: Expiry
expiry_list = get_expiry(SECURITY_ID)

if expiry_list:
    expiry = st.selectbox("Select Expiry", expiry_list)

    # 🔥 Step 2: Option Chain
    data = get_option_chain(SECURITY_ID, expiry)

    st.subheader("Option Chain Raw Response")
    st.json(data)

    if "data" in data:
        st.success("✅ Option Chain Loaded")
    else:
        st.warning("Option chain empty")

else:
    st.error("❌ Expiry not loaded")
