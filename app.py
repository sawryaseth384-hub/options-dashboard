import streamlit as st
from core.token_manager import get_headers
from dhan_data.expiry import get_expiry
from dhan_data.option_chain import get_option_chain

st.set_page_config(page_title="Dhan Options Dashboard", layout="wide")

st.title("📊 Dhan Options Dashboard")

# =========================
# Step 1: Symbol
# =========================
symbol = st.text_input("Symbol", "NIFTY")

# For now fixed (NIFTY)
SECURITY_ID = 13
st.write(f"🔍 {symbol} security ID:", SECURITY_ID)

# =========================
# Step 2: Get Expiry
# =========================
expiry_list = []

try:
    expiry_data = get_expiry(SECURITY_ID)

    # Debug
    st.write("📦 Expiry Raw:", expiry_data)

    if expiry_data and "data" in expiry_data:
        expiry_list = expiry_data["data"]

except Exception as e:
    st.error(f"Expiry Error: {e}")

# =========================
# Step 3: Select Expiry
# =========================
if expiry_list:
    expiry = st.selectbox("Select Expiry", expiry_list)
else:
    st.warning("No expiry data found")
    st.stop()

# =========================
# Step 4: Option Chain
# =========================
st.subheader("📊 Option Chain")

try:
    option_data = get_option_chain(SECURITY_ID, expiry)

    # 🔥 RAW DEBUG (MOST IMPORTANT)
    st.write("📦 Raw API Response:", option_data)

    # =========================
    # Handle Response
    # =========================
    if option_data is None:
        st.error("❌ No response from API")

    elif "error" in option_data:
        st.error(f"❌ Error: {option_data['error']}")

    elif "data" in option_data:
        st.success("✅ Option Chain Loaded")

        # Show raw data
        st.json(option_data["data"])

    else:
        st.warning("⚠️ Unexpected response format")
        st.write(option_data)

except Exception as e:
    st.error(f"❌ Option Chain Error: {e}")
