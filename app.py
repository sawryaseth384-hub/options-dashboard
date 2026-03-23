import streamlit as st
from dhan_data.expiry import get_expiry
from dhan_data.option_chain import get_option_chain

st.title("Dhan Options Dashboard")

# Fixed NIFTY ID
security_id = 13

st.write(f"🔍 NIFTY security ID: {security_id}")

# ✅ Step 1: expiry fetch
expiry_list = get_expiry(security_id)

if expiry_list:
    
    # ✅ Step 2: user select
    expiry = st.selectbox("Select Expiry", expiry_list)

    # ✅ Step 3: API call (expiry now defined)
    data = get_option_chain(security_id, expiry)

    st.write("Option Chain Raw Response")
    st.json(data)

else:
    st.error("❌ No expiry found")
