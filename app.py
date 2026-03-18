import streamlit as st

st.set_page_config(page_title="AI Trading Dashboard", layout="wide")

st.title("🚀 AI Trading Dashboard")

# ✅ CORRECT SECRET KEYS (MATCH WITH YOUR SECRETS)
try:
    CLIENT_ID = st.secrets["DHAN_CLIENT_ID"]
    ACCESS_TOKEN = st.secrets["DHAN_ACCESS_TOKEN"]

    st.success("CLIENT_ID Loaded ✅")
    st.success("ACCESS_TOKEN Loaded ✅")

except Exception as e:
    st.error(f"Secrets Error: {e}")
    st.stop()


# 🚀 MODULE CHECK
st.subheader("📦 Module Status")

# Market Quote
try:
    from market_quote import MarketQuote
    st.success("MarketQuote → ✅ Loaded")
except Exception as e:
    st.error(f"MarketQuote → ❌ Error: {e}")

# Data Processor
try:
    from ai_engine.data_processor import DataProcessor
    st.success("DataProcessor → ✅ Loaded")
except Exception as e:
    st.error(f"DataProcessor → ❌ Error: {e}")

# Signal Engine
try:
    from ai_engine.signal_engine import SignalEngine
    st.success("SignalEngine → ✅ Loaded")
except Exception as e:
    st.error(f"SignalEngine → ❌ Error: {e}")


# 🚀 API TEST BUTTON
st.subheader("🧪 API Test")

if st.button("Test Market Quote API"):
    try:
        from market_quote import MarketQuote

        mq = MarketQuote()

        instruments = {
            "NSE_FNO": [49081]
        }

        data = mq.get_data(instruments)

        st.json(data)

    except Exception as e:
        st.error(f"API Error: {e}")
