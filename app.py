import streamlit as st
from utils.config import ACCESS_TOKEN, CLIENT_ID
from ai_engine.market_quote import MarketQuote

st.title("📊 AI Trading Dashboard")

# 🔍 CONFIG STATUS
st.subheader("⚙️ Config Status")

if ACCESS_TOKEN:
    st.success("ACCESS_TOKEN Loaded")
else:
    st.error("ACCESS_TOKEN Missing")

if CLIENT_ID:
    st.success("CLIENT_ID Loaded")
else:
    st.error("CLIENT_ID Missing")

# 🧠 API TEST
st.subheader("🔍 Live Market Test")

if st.button("Fetch Market Data"):

    try:
        mq = MarketQuote()

        data = mq.get_data({
            "NSE_FNO": [49081]
        })

        st.write("API Response:")
        st.json(data)

        if data.get("status") == "success":
            st.success("API Working ✅")
        else:
            st.error("API Failed ❌")

    except Exception as e:
        st.error(f"Error: {str(e)}")
