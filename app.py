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

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="🔥 AI Trading System", layout="wide")

# =========================
# STYLE
# =========================
st.markdown("""
<style>
body {background-color:#0b0f1a;}

.card {
    background:#111827;
    padding:12px;
    border-radius:10px;
    border:1px solid #1f2937;
}

.ticker {
    display:flex;
    gap:10px;
    overflow-x:auto;
    padding:8px;
    background:#020617;
    border-radius:8px;
}

.ticker-item {
    min-width:100px;
    padding:6px;
    background:#0f172a;
    border-radius:6px;
    text-align:center;
    font-size:12px;
}

.green {color:#22c55e;}
.red {color:#ef4444;}
</style>
""", unsafe_allow_html=True)

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

# =========================
# TICKER
# =========================
st.markdown("""
<div class="ticker">
    <div class="ticker-item"><b>NIFTY</b><br>22450 <span class="green">+120</span></div>
    <div class="ticker-item"><b>BANKNIFTY</b><br>48200 <span class="green">+300</span></div>
    <div class="ticker-item"><b>SENSEX</b><br>74500 <span class="green">+250</span></div>
    <div class="ticker-item"><b>DOW</b><br>38500 <span class="green">+200</span></div>
</div>
""", unsafe_allow_html=True)

st.divider()

if not symbol:
    st.stop()

# =========================
# FETCH DATA
# =========================
try:
    data = dhan_api.get_full_data(symbol)
except Exception as e:
    st.error(f"❌ API Error: {e}")
    st.stop()

if not data or "error" in data:
    st.error(data.get("error", "Invalid Symbol"))
    st.stop()

# =========================
# WS START
# =========================
if "ws_started" not in st.session_state:
    try:
        start_live_feed()
        start_depth_feed()
        st.session_state.ws_started = True
    except:
        pass

# =========================
# SUBSCRIBE
# =========================
if "subscribed_symbol" not in st.session_state or st.session_state.subscribed_symbol != symbol:
    try:
        subscribe_instrument(data["security_id"], data["segment"])
        subscribe_depth(data["security_id"], data["segment"])
        st.session_state.subscribed_symbol = symbol
    except:
        pass

# =========================
# LIVE PRICE FIX
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

    expiry = None
    if data.get("expiries"):
        expiry = st.selectbox("Expiry", data["expiries"])

    st.markdown("### 📊 Option Chain")

    if expiry:
        try:
            option_data = dhan_api.fetch_option_chain(
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
                        "Call Delta": ce.get("greeks", {}).get("delta", 0),
                        "Call IV": ce.get("implied_volatility", 0),

                        "Put OI": pe.get("oi", 0),
                        "Put LTP": pe.get("last_price", 0),
                        "Put Delta": pe.get("greeks", {}).get("delta", 0),
                        "Put IV": pe.get("implied_volatility", 0),
                    })

                except:
                    continue

            df = pd.DataFrame(rows).sort_values("Strike")

            # 🔥 ATM Highlight
            atm = min(df["Strike"], key=lambda x: abs(x - spot))

            def highlight(row):
                if row["Strike"] == atm:
                    return ["background-color: #1e293b"] * len(row)
                return [""] * len(row)

            st.dataframe(df.style.apply(highlight, axis=1), use_container_width=True)

            # 🔥 AI SIGNAL
            st.markdown("## 🤖 AI Signal")

            call_oi = df["Call OI"].sum()
            put_oi = df["Put OI"].sum()

            if put_oi > call_oi:
                st.success("📈 BUY CALL")
            elif call_oi > put_oi:
                st.error("📉 BUY PUT")
            else:
                st.warning("⚖️ WAIT")

        except Exception as e:
            st.error(f"Option Error: {e}")

    # 🔥 MARKET DEPTH
    st.markdown("### 📊 Market Depth")

    depth = get_depth()

    colA, colB = st.columns(2)

    with colA:
        st.subheader("Bids")
        st.dataframe(depth.get("bids", []))

    with colB:
        st.subheader("Asks")
        st.dataframe(depth.get("asks", []))


# ============================================================
# STOCK DASHBOARD
# ============================================================
with tab2:

    col1, col2 = st.columns([2,5])

    with col1:
        st.markdown("### 📋 Watchlist")
        st.write(["RELIANCE", "TCS", "SBIN"])

    with col2:
        st.markdown("### 📈 Chart")

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


# ============================================================
# WAR ROOM
# ============================================================
with tab3:

    st.markdown("## 🧠 War Room")

    cols = st.slider("Columns", 1, 4, 2)
    grid = st.columns(cols)

    panels = ["NIFTY","BANKNIFTY","OI","FII/DII","Depth","AI"]

    selected = st.multiselect("Panels", panels, default=panels[:cols])

    for i, p in enumerate(selected):
        with grid[i % cols]:

            st.markdown('<div class="card">', unsafe_allow_html=True)

            if p == "NIFTY":
                st.metric("NIFTY", spot)

            elif p == "BANKNIFTY":
                st.metric("BANKNIFTY", "48,200")

            elif p == "OI":
                st.info("OI Analysis")

            elif p == "FII/DII":
                st.metric("FII", "+1200Cr")
                st.metric("DII", "-500Cr")

            elif p == "Depth":
                depth = get_depth()
                st.dataframe(depth.get("bids", []))

            elif p == "AI":
                st.success("BUY CALL")
                st.warning("Avoid PE")

            st.markdown('</div>', unsafe_allow_html=True)

# ================= DEBUG =================
with st.expander("Debug"):
    st.json(data)
