import streamlit as st
from dhanhq import DhanContext, dhanhq

# =============================
# 🔐 LOAD SECRETS
# =============================
try:
    client_id = st.secrets["DHAN_CLIENT_ID"]
    access_token = st.secrets["DHAN_ACCESS_TOKEN"]
except Exception as e:
    st.error("❌ Secrets load नहीं हो रहे")
    st.stop()

# =============================
# 🚀 CONNECT DHAN
# =============================
try:
    dhan_context = DhanContext(client_id, access_token)
    dhan = dhanhq(dhan_context)

    st.success("✅ Dhan Connected Successfully")

    # Debug info
    st.write("Client ID:", client_id)
    st.write("Token Length:", len(access_token))

except Exception as e:
    st.error("❌ Dhan Connection Failed")
    st.write(e)
    st.stop()

# =============================
# 📊 API TEST BUTTON
# =============================
st.header("🔍 API Test")

if st.button("Test Market Data"):

    try:
        # Sample instrument (N
