import streamlit as st
import traceback

# 🔥 PAGE CONFIG
st.set_page_config(page_title="AI Trading Dashboard", layout="wide")

st.title("🚀 AI Trading Dashboard")

# =========================
# 🔐 CONFIG CHECK
# =========================
st.header("⚙️ Config Status")

try:
    CLIENT_ID = st.secrets["CLIENT_ID"]
    ACCESS_TOKEN = st.secrets["ACCESS_TOKEN"]

    st.success("✅ CLIENT_ID Loaded")
    st.success("✅ ACCESS_TOKEN Loaded")

except Exception as e:
    st.error("❌ Secrets Error")
    st.code(traceback.format_exc())
    st.stop()

# =========================
# 📦 IMPORT MODULE CHECK
# =========================
st.header("📦 Module Status")

modules = {}

try:
    from ai_engine.market_quote import MarketQuote
    modules["MarketQuote"] = "✅ Loaded"
except:
    modules["MarketQuote"] = "❌ Error"

try:
    from ai_engine.data_processor import DataProcessor
    modules["DataProcessor"] = "✅ Loaded"
except:
    modules["DataProcessor"] = "❌ Error"

try:
    from ai_engine.signal_engine import SignalEngine
    modules["SignalEngine"] = "✅ Loaded"
except:
    modules["SignalEngine"] = "❌ Error"

# show module status
for k, v in modules.items():
    st.write(f"{k} → {v}")

# =========================
# 🚀 AI ENGINE CONTROL PANEL
# =========================
st.header("🚀 AI Engine Control Panel")

if "❌ Error" in modules.values():
    st.warning("⚠️ Fix modules first")
    st.stop()

# init
mq = MarketQuote()
dp = DataProcessor()
se = SignalEngine()

# =========================
# 🎯 INPUT SECTION
# =========================
st.subheader("🎯 Instrument Selection")

segment = st.selectbox("Segment", ["NSE_EQ", "NSE_FNO"])
instrument_id = st.number_input("Instrument ID", value=11536)

payload = {
    segment: [int(instrument_id)]
}

# =========================
# 🔍 RUN ENGINE
# =========================
if st.button("🔥 Run AI Engine"):

    try:
        st.info("📡 Fetching Data...")

        data = mq.get_data(payload)

        # 🔥 RAW DEBUG
        with st.expander("🔍 Raw API Response"):
            st.json(data)

        if data.get("status") == "error":
            st.error("❌ API Error")
            st.json(data)
            st.stop()

        # =========================
        # 📊 PROCESS DATA
        # =========================
        ltp = dp.extract_ltp(data, segment, instrument_id)
        oi = dp.extract_oi(data, segment, instrument_id)
        vol = dp.extract_volume(data, segment, instrument_id)

        st.subheader("📊 Market Data")

        col1, col2, col3 = st.columns(3)

        col1.metric("LTP", ltp)
        col2.metric("OI", oi)
        col3.metric("Volume", vol)

        # =========================
        # 🤖 AI SIGNAL
        # =========================
        signal = se.generate_signal(ltp, oi, vol)

        st.subheader("🤖 AI Signal")

        if signal == "STRONG TREND":
            st.success(signal)
        elif signal == "MOMENTUM":
            st.warning(signal)
        else:
            st.info(signal)

    except Exception as e:
        st.error("💥 Engine Crash")
        st.code(traceback.format_exc())
