import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests

from core.token_manager import get_token
from dhan_data.instruments import get_symbol_data
from dhan_data.option_chain import get_option_chain
from dhan_data.live_market_feed import start_live_feed, subscribe_instrument, get_live_ltp
from dhan_data.depth_feed import start_depth_feed, subscribe_depth, get_depth
from dhan_data.market_quote import get_ltp

st.set_page_config(page_title="🔥 AI Option Trading System", layout="wide")

# ---- Header ----
col1, col2, col3 = st.columns([2, 4, 2])
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

# ---- Get symbol data ----
security_id, segment = get_symbol_data(symbol)
if security_id is None:
    st.error("Invalid Symbol")
    st.stop()

# ---- Start WebSockets ----
if "ws_started" not in st.session_state:
    start_live_feed()
    start_depth_feed()
    st.session_state.ws_started = True

# ---- Subscribe ----
if "subscribed_symbol" not in st.session_state or st.session_state.subscribed_symbol != symbol:
    try:
        subscribe_instrument(security_id, segment)
        subscribe_depth(security_id, segment)
        st.session_state.subscribed_symbol = symbol
    except Exception as e:
        st.error(f"Subscribe Error: {e}")

# ---- Spot Price ----
live_price = get_live_ltp()
if live_price == 0:
    live_price = get_ltp(security_id, segment)

spot = live_price

# ---- HEADERS (FIXED) ----
headers = {
    "access-token": get_token(),
    "client-id": st.secrets["DHAN_CLIENT_ID"],
    "Content-Type": "application/json"
}

# ---- Fetch Expiry List ----
url = "https://api.dhan.co/v2/optionchain/expirylist"
payload = {
    "UnderlyingScrip": security_id,
    "UnderlyingSeg": "IDX_I"
}

try:
    resp = requests.post(url, headers=headers, json=payload)
    data = resp.json()
except Exception as e:
    st.error(f"Expiry API Error: {e}")
    st.stop()

expiries = data.get("data", []) if data.get("status") == "success" else []

if not expiries:
    st.error("No expiry dates found. Check token or Data API subscription.")
    st.stop()

# ---- Tabs ----
tab1, tab2, tab3 = st.tabs(["📊 Option", "📈 Stock", "🧠 War Room"])

with tab1:

    expiry = st.selectbox("Expiry", expiries)

    option_data = get_option_chain(security_id, segment, expiry)

    if not option_data or "data" not in option_data:
        st.error("No option data received")
        st.stop()

    oc = option_data["data"].get("oc", {})

    if not oc:
        st.warning("Option chain empty")
        st.json(option_data)
        st.stop()

    # ---- DataFrame ----
    rows = []
    for strike_str, opts in oc.items():
        try:
            strike = float(strike_str)
            ce = opts.get("ce", {})
            pe = opts.get("pe", {})

            rows.append({
                "Strike": strike,
                "Call OI": ce.get("oi", 0),
                "Call LTP": ce.get("last_price", 0),
                "Call IV": ce.get("implied_volatility", 0),
                "Call Delta": ce.get("greeks", {}).get("delta", 0),
                "Put OI": pe.get("oi", 0),
                "Put LTP": pe.get("last_price", 0),
                "Put IV": pe.get("implied_volatility", 0),
                "Put Delta": pe.get("greeks", {}).get("delta", 0),
            })
        except:
            continue

    df = pd.DataFrame(rows).sort_values("Strike")

    if df.empty:
        st.warning("No option data parsed")
        st.stop()

    # ---- Analytics ----
    total_call_oi = df["Call OI"].sum()
    total_put_oi = df["Put OI"].sum()

    pcr = total_put_oi / total_call_oi if total_call_oi else 0

    atm_strike = df.iloc[(df["Strike"] - spot).abs().argsort()[:1]]["Strike"].values[0]
    atm_row = df[df["Strike"] == atm_strike].iloc[0]

    call_strength = atm_row["Call OI"] / total_call_oi * 100 if total_call_oi else 0
    put_strength = atm_row["Put OI"] / total_put_oi * 100 if total_put_oi else 0

    # ---- Signal ----
    if pcr > 1.2:
        signal = "📉 BEARISH"
    elif pcr < 0.8:
        signal = "📈 BULLISH"
    else:
        signal = "⚖️ NEUTRAL"

    # ---- Metrics ----
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Spot", f"{spot:,.2f}")
    col2.metric("PCR", f"{pcr:.2f}")
    col3.metric("ATM", f"{atm_strike:.0f}")
    col4.metric("Signal", signal)

    # ---- Table ----
    st.subheader("📋 Option Chain")
    st.dataframe(df, use_container_width=True)

    # ---- Chart ----
    st.subheader("📊 OI Chart")
    st.bar_chart(df.set_index("Strike")[["Call OI", "Put OI"]])

    # ---- Depth ----
    depth = get_depth()
    st.subheader("📊 Market Depth")

    colA, colB = st.columns(2)
    colA.dataframe(depth.get("bids", []))
    colB.dataframe(depth.get("asks", []))


with tab2:
    st.info("Stock chart coming soon")

with tab3:
    st.write("War Room Active")

st.caption("Auto token system active ✅")
