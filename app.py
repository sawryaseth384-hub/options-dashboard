import streamlit as st
from core import dhan_api
import pandas as pd
import plotly.graph_objects as go

from dhan_data.live_market_feed import (
    start_live_feed,
    subscribe_instrument,
    get_live_ltp
)

from dhan_data.depth_feed import (
    start_depth_feed,
    subscribe_depth,
    get_depth
)

from dhan_data.market_quote import get_ltp
from dhan_data.option_chain import get_option_chain  # 🔥 NEW

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="🔥 AI Trading System", layout="wide")

# =========================
# HEADER
# =========================
col1, col2, col3 = st.columns([2,4,2])

with col1:
    st.markdown("## 🔥 SHREE AI")

with col2:
    symbol = st.text_input("🔍 Search Symbol", value="NIFTY").upper()

with col3:
    st.metric("💰 Balance", "₹1,00,000")
    st.metric("📊 P&L", "+₹2,500")

st.divider()

if not symbol:
    st.stop()

# =========================
# FETCH DATA
# =========================
data = dhan_api.get_full_data(symbol)

if not data or "error" in data:
    st.error("Invalid Symbol")
    st.stop()

# =========================
# WS START
# =========================
if "ws_started" not in st.session_state:
    start_live_feed()
    start_depth_feed()
    st.session_state.ws_started = True

# =========================
# 🔥 SEGMENT FIX
# =========================
segment = data["segment"]

if "IDX" in segment:
    segment = "NSE_FNO"

# =========================
# SUBSCRIBE
# =========================
if "subscribed_symbol" not in st.session_state or st.session_state.subscribed_symbol != symbol:
    try:
        subscribe_instrument(data["security_id"], segment)
        subscribe_depth(data["security_id"], segment)
        st.session_state.subscribed_symbol = symbol
    except Exception as e:
        st.error(f"Subscribe Error: {e}")

# =========================
# 🔥 LIVE PRICE FIX
# =========================
live_price = get_live_ltp()

if live_price == 0:
    live_price = get_ltp(data["security_id"], data["segment"])

spot = live_price

# =========================
# TABS
# =========================
tab1, tab2, tab3 = st.tabs(["📊 Option", "📈 Stock", "🧠 War Room"])

# ============================================================
# OPTION DASHBOARD
# ============================================================
with tab1:

    col1, col2, col3 = st.columns(3)
    col1.metric("Symbol", data.get("symbol"))
    col2.metric("Spot", spot)
    col3.metric("Segment", data.get("segment"))

    st.write("Expiries:", data.get("expiries"))  # 🔥 DEBUG

    expiry = None
    if data.get("expiries"):
        expiry = st.selectbox("Expiry", data["expiries"])

    if expiry:

        option_data = get_option_chain(   # 🔥 FIXED
            data["security_id"],
            data["segment"],
            expiry
        )

        if not option_data or "data" not in option_data:
            st.error("No option data")
            st.stop()

        oc = option_data["data"].get("oc", {})

        if not oc:
            st.warning("Option Chain Empty")
            st.stop()

        rows = []

        for strike, val in oc.items():
            try:
                strike = float(strike)

                ce = val.get("ce", {})
                pe = val.get("pe", {})

                rows.append({
                    "Strike": strike,
                    "Call OI": ce.get("oi", 0),
                    "Call LTP": ce.get("last_price", 0),
                    "Put OI": pe.get("oi", 0),
                    "Put LTP": pe.get("last_price", 0),
                })
            except:
                continue

        df = pd.DataFrame(rows).sort_values("Strike")

        st.dataframe(df, use_container_width=True)

    # ================= DEPTH =================
    st.markdown("### Market Depth")

    depth = get_depth()

    st.write("Bids:", depth.get("bids", []))
    st.write("Asks:", depth.get("asks", []))


# ============================================================
# STOCK
# ============================================================
with tab2:

    hist = data.get("historical", [])

    if hist:
        df_chart = pd.DataFrame(hist)

        fig = go.Figure(data=[go.Candlestick(
            x=df_chart["time"],
            open=df_chart["open"],
            high=df_chart["high"],
            low=df_chart["low"],
            close=df_chart["close"]
        )])

        st.plotly_chart(fig, use_container_width=True)


# ============================================================
# WAR ROOM
# ============================================================
with tab3:
    st.write("War Room Active")
