import streamlit as st
from dhanhq import DhanContext, dhanhq

# =============================
# 🔐 LOAD SECRETS
# =============================
client_id = st.secrets["DHAN_CLIENT_ID"]
access_token = st.secrets["DHAN_ACCESS_TOKEN"]

# =============================
# 🚀 CONNECT DHAN
# =============================
dhan_context = DhanContext(client_id, access_token)
dhan = dhanhq(dhan_context)

st.success("✅ Dhan Connected")

st.write("Client ID:", client_id)
st.write("Token Length:", len(access_token))

# =============================
# 📊 API TEST
# =============================
st.header("API Test")

if st.button("Test Market Data"):

    try:
        # 👇 IMPORTANT: indentation सही
        instruments = {
            "NSE_EQ": [11536]
        }

        data = dhan.market_quote(instruments)

        st.success("✅ API Working")
        st.json(data)

    except Exception as e:
        st.error("❌ API Failed")
        st.write(e)
