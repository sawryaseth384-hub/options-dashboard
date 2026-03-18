import streamlit as st

st.title("🚀 AI Trading Dashboard")

# ✅ DIRECT KEYS (NO DHAN_)
try:
    CLIENT_ID = st.secrets["CLIENT_ID"]
    ACCESS_TOKEN = st.secrets["ACCESS_TOKEN"]

    st.success("CLIENT_ID Loaded ✅")
    st.success("ACCESS_TOKEN Loaded ✅")

except Exception as e:
    st.error(f"Secrets Error: {e}")
    st.stop()


# 🔥 MODULE CHECK
st.subheader("📦 Module Status")

try:
    from market_quote import MarketQuote
    st.success("MarketQuote → ✅ Loaded")
except Exception as e:
    st.error(f"MarketQuote → ❌ {e}")

try:
    from ai_engine.data_processor import DataProcessor
    st.success("DataProcessor → ✅ Loaded")
except Exception as e:
    st.error(f"DataProcessor → ❌ {e}")

try:
    from ai_engine.signal_engine import SignalEngine
    st.success("SignalEngine → ✅ Loaded")
except Exception as e:
    st.error(f"SignalEngine → ❌ {e}")
