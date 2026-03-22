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
from dhan_data.option_chain import get_option_chain

st.set_page_config(page_title="🔥 AI Trading System", layout="wide")

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

data = dhan_api.get_full_data(symbol)
if not data or "error" in data:
    st.error("Invalid Symbol")
    st.stop()

# 🔥 FIX: Convert segment for option chain & depth
segment = data["segment"]
if segment in ["IDX_I", "D"]:
    segment = "NSE_FNO"    # options always use NSE_FNO

# Start WebSockets if not started
if "ws_started" not in st.session_state:
    start_live_feed()
    start_depth_feed()
    st.session_state.ws_started = True

# Subscribe only once per symbol
if "subscribed_symbol" not in st.session_state or st.session_state.subscribed_symbol != symbol:
    try:
        # Use the converted segment for subscriptions
        subscribe_instrument(data["security_id"], segment)
        subscribe_depth(data["security_id"], segment)
        st.session_state.subscribed_symbol = symbol
    except Exception as e:
        st.error(f"Subscribe Error: {e}")

live_price = get_live_ltp()
if live_price == 0:
    live_price = get_ltp(data["security_id"], data["segment"])   # original segment for LTP

spot = live_price

tab1, tab2, tab3 = st.tabs(["📊 Option", "📈 Stock", "🧠 War Room"])

with tab1:
    col1, col2, col3 = st.columns(3)
    col1.metric("Symbol", data.get("symbol"))
    col2.metric("Spot", spot)
    col3.metric("Segment", segment)

    expiry = None
    if data.get("expiries"):
        expiry = st.selectbox("Expiry", data["expiries"])

    if expiry:
        # Use the converted segment (NSE_FNO) for option chain
        option_data = get_option_chain(data["security_id"], segment, expiry)

        if not option_data or "data" not in option_data:
            st.error("No option data")
            st.stop()

        oc = option_data["data"].get("oc", {})
        if not oc:
            st.warning("Option Chain Empty")
            st.stop()

        rows = []
        for strike, options in oc.items():
            try:
                strike = float(strike)
                ce = options.get("ce", {})
                pe = options.get("pe", {})
                rows.append({
                    "Strike": strike,
                    "Call OI": ce.get("oi", 0),
                    "Call LTP": ce.get("last_price", 0),
                    "Call Delta": ce.get("greeks", {}).get("delta", 0),
                    "Call Theta": ce.get("greeks", {}).get("theta", 0),
                    "Call Gamma": ce.get("greeks", {}).get("gamma", 0),
                    "Call Vega": ce.get("greeks", {}).get("vega", 0),
                    "Call IV": ce.get("implied_volatility", 0),
                    "Put OI": pe.get("oi", 0),
                    "Put LTP": pe.get("last_price", 0),
                    "Put Delta": pe.get("greeks", {}).get("delta", 0),
                    "Put Theta": pe.get("greeks", {}).get("theta", 0),
                    "Put Gamma": pe.get("greeks", {}).get("gamma", 0),
                    "Put Vega": pe.get("greeks", {}).get("vega", 0),
                    "Put IV": pe.get("implied_volatility", 0),
                })
            except:
                continue

        df = pd.DataFrame(rows)
        if df.empty:
            st.warning("No option data parsed")
            st.stop()

        df = df.sort_values("Strike")

        atm = None
        if spot > 0:
            atm = min(df["Strike"], key=lambda x: abs(x - spot))

        def highlight(row):
            if atm and row["Strike"] == atm:
                return ["background-color: #1e293b"] * len(row)
            return [""] * len(row)

        st.dataframe(df.style.apply(highlight, axis=1), use_container_width=True)

        st.markdown("## 🤖 AI Signal")
        call_oi = df["Call OI"].sum()
        put_oi = df["Put OI"].sum()
        if put_oi > call_oi:
            st.success("📈 BUY CALL (Bullish)")
        elif call_oi > put_oi:
            st.error("📉 BUY PUT (Bearish)")
        else:
            st.warning("⚖️ WAIT")

    st.markdown("### 📊 Market Depth")
    depth = get_depth()
    colA, colB = st.columns(2)
    with colA:
        st.subheader("Bids")
        st.dataframe(depth.get("bids", []))
    with colB:
        st.subheader("Asks")
        st.dataframe(depth.get("asks", []))

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
        fig.update_layout(template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.write("War Room Active")
