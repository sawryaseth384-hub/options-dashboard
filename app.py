import streamlit as st
from core import dhan_api
import pandas as pd
import plotly.graph_objects as go

# 🔌 LIVE FEED
from dhan_data.live_market_feed import (
    start_live_feed,
    subscribe_instrument,
    get_live_ltp
)

# 🔌 DEPTH FEED
from dhan_data.depth_feed import (
    start_depth_feed,
    subscribe_depth,
    get_depth
)

# =========================
# 🔥 PAGE CONFIG
# =========================
st.set_page_config(page_title="🔥 Dhan Full System", layout="wide")
st.title("📈 Dhan AI Full Options Dashboard")

# =========================
# 🎯 SYMBOL INPUT
# =========================
symbol = st.text_input(
    "Enter Symbol (NIFTY / BANKNIFTY / RELIANCE / SBIN)",
    value="NIFTY"
).upper()

if not symbol:
    st.stop()

# =========================
# 🚀 FETCH FULL DATA
# =========================
try:
    data = dhan_api.get_full_data(symbol)
except Exception as e:
    st.error(f"❌ API Error: {e}")
    st.stop()

if not data or "error" in data:
    st.error(data.get("error", "Invalid Symbol / API Issue"))
    st.stop()

# =========================
# 🔌 START WS (ONLY ONCE)
# =========================
if "ws_started" not in st.session_state:
    try:
        start_live_feed()
        start_depth_feed()
        st.session_state.ws_started = True
    except Exception as e:
        st.warning(f"⚠️ WebSocket Error: {e}")

# =========================
# 📡 SUBSCRIBE (ONCE PER SYMBOL)
# =========================
if (
    "subscribed_symbol" not in st.session_state or
    st.session_state.subscribed_symbol != symbol
):
    try:
        subscribe_instrument(data["security_id"], data["segment"])
        subscribe_depth(data["security_id"], data["segment"])
        st.session_state.subscribed_symbol = symbol
    except Exception as e:
        st.warning(f"⚠️ Subscribe Error: {e}")

# =========================
# 💰 LIVE LTP
# =========================
live_price = get_live_ltp()
spot = live_price if live_price != 0 else data.get("ltp", 0)

# =========================
# 📊 BASIC INFO
# =========================
col1, col2, col3 = st.columns(3)

col1.metric("Symbol", data.get("symbol", "-"))
col2.metric("Spot (LTP)", spot)
col3.metric("Segment", data.get("segment", "-"))

st.caption(f"Security ID: {data.get('security_id')}")

# =========================
# 📅 EXPIRY SELECT
# =========================
expiry = None

if data.get("expiries"):
    expiry = st.selectbox("Select Expiry", data["expiries"])
else:
    st.warning("No expiry data available")

# =========================
# 📊 OPTION CHAIN
# =========================
st.markdown("## 📊 Option Chain")

if expiry:
    try:
        option_data = dhan_api.fetch_option_chain(
            data["security_id"],
            data["segment"],
            expiry
        )

        if option_data and "data" in option_data:
            oc = option_data["data"].get("oc", {})

            rows = []

            for strike, val in oc.items():
                ce = val.get("ce", {})
                pe = val.get("pe", {})

                rows.append({
                    "Strike": float(strike),
                    "Call OI": ce.get("oi", 0),
                    "Call LTP": ce.get("last_price", 0),
                    "Put OI": pe.get("oi", 0),
                    "Put LTP": pe.get("last_price", 0)
                })

            df = pd.DataFrame(rows).sort_values("Strike")

            st.dataframe(df, use_container_width=True)

        else:
            st.warning("No option chain data")

    except Exception as e:
        st.error(f"Option Chain Error: {e}")

# =========================
# 📈 HISTORICAL CHART
# =========================
st.markdown("## 📈 Price Chart")

hist = data.get("historical", [])

if hist:
    try:
        df = pd.DataFrame(hist)

        fig = go.Figure(data=[go.Candlestick(
            x=df["time"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"]
        )])

        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Chart Error: {e}")
else:
    st.warning("No historical data")

# =========================
# 📦 EXPIRED OPTIONS
# =========================
st.markdown("## 📦 Expired Options")

expired = data.get("expired", [])

if expired:
    st.json(expired)
else:
    st.warning("No expired options data")

# =========================
# 📊 MARKET DEPTH
# =========================
st.markdown("## 📊 Market Depth")

depth = get_depth()

col1, col2 = st.columns(2)

with col1:
    st.subheader("Bids")
    st.dataframe(depth.get("bids", []), use_container_width=True)

with col2:
    st.subheader("Asks")
    st.dataframe(depth.get("asks", []), use_container_width=True)

# =========================
# 🔍 DEBUG PANEL
# =========================
with st.expander("🔍 Debug Info"):
    st.json(data)
