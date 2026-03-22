import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from core.token_manager import get_headers
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

# ---- Start WebSockets (once) ----
if "ws_started" not in st.session_state:
    start_live_feed()
    start_depth_feed()
    st.session_state.ws_started = True

# Subscribe only once
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

# ---- Fetch Expiry List (via API) ----
url = "https://api.dhan.co/v2/optionchain/expirylist"
payload = {"UnderlyingScrip": security_id, "UnderlyingSeg": "IDX_I"}
resp = requests.post(url, headers=get_headers(), json=payload)
expiries = []
if resp.status_code == 200 and resp.json().get("status") == "success":
    expiries = resp.json().get("data", [])

if not expiries:
    st.error("No expiry dates found. Check token or Data API subscription.")
    st.stop()

# ---- Tabs ----
tab1, tab2, tab3 = st.tabs(["📊 Option", "📈 Stock", "🧠 War Room"])

with tab1:
    # ---- Expiry Selection ----
    expiry = st.selectbox("Expiry", expiries)

    # ---- Fetch Option Chain ----
    option_data = get_option_chain(security_id, segment, expiry)
    if not option_data or "data" not in option_data:
        st.error("No option data received")
        st.stop()

    oc = option_data["data"].get("oc", {})
    if not oc:
        st.warning("Option chain empty")
        with st.expander("Raw API Response"):
            st.json(option_data)
        st.stop()

    # ---- Convert to DataFrame ----
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
        except Exception as e:
            continue

    df = pd.DataFrame(rows).sort_values("Strike")
    if df.empty:
        st.warning("No option data parsed")
        st.stop()

    # ---- Analytics ----
    total_call_oi = df["Call OI"].sum()
    total_put_oi = df["Put OI"].sum()
    pcr = total_put_oi / total_call_oi if total_call_oi > 0 else 0

    # ATM strike
    atm_strike = df.iloc[(df["Strike"] - spot).abs().argsort()[:1]]["Strike"].values[0]
    atm_row = df[df["Strike"] == atm_strike].iloc[0]
    call_strength = atm_row["Call OI"] / total_call_oi * 100 if total_call_oi else 0
    put_strength = atm_row["Put OI"] / total_put_oi * 100 if total_put_oi else 0

    # AI Signal
    if pcr > 1.2:
        signal = "📉 BEARISH (High Put OI)"
    elif pcr < 0.8:
        signal = "📈 BULLISH (High Call OI)"
    else:
        signal = "⚖️ NEUTRAL with Call Bias" if call_strength > put_strength else "⚖️ NEUTRAL with Put Bias"

    # ---- Display Metrics ----
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Spot Price", f"{spot:,.2f}")
    col2.metric("Put‑Call Ratio (PCR)", f"{pcr:.2f}")
    col3.metric("ATM Strike", f"{atm_strike:.0f}")
    col4.metric("AI Signal", signal)

    # ---- Top OI Strikes ----
    st.subheader("📊 Top OI Strikes")
    top_oi = df.nlargest(5, "Call OI")[["Strike", "Call OI", "Put OI"]]
    st.dataframe(top_oi, use_container_width=True)

    # ---- Full Option Chain ----
    st.subheader("📋 Full Option Chain")
    st.dataframe(df.style.format({
        "Call OI": "{:,.0f}", "Put OI": "{:,.0f}",
        "Call LTP": "{:.2f}", "Put LTP": "{:.2f}",
        "Call IV": "{:.2f}%", "Put IV": "{:.2f}%",
        "Call Delta": "{:.3f}", "Put Delta": "{:.3f}"
    }), use_container_width=True)

    # ---- OI Distribution Chart ----
    st.subheader("📈 OI Distribution (ATM ± 5 strikes)")
    atm_index = df[df["Strike"] == atm_strike].index[0]
    start = max(0, atm_index - 5)
    end = min(len(df), atm_index + 6)
    oi_subset = df.iloc[start:end][["Strike", "Call OI", "Put OI"]].set_index("Strike")
    st.bar_chart(oi_subset)

    # ---- Market Depth ----
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
    st.info("Stock chart coming soon")
    # You can later integrate historical data here

with tab3:
    st.write("War Room Active")

st.caption("Data refreshes on page reload. Token auto‑refreshes every 24h.")
