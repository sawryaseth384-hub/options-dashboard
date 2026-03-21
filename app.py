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

# =========================
# 🎨 GLOBAL STYLE (🔥 PRO UI)
# =========================
st.set_page_config(page_title="🔥 AI Trading System", layout="wide")

st.markdown("""
<style>
body {background-color:#0b0f1a;}

.block-container {padding-top:1rem;}

.card {
    background:#111827;
    padding:15px;
    border-radius:12px;
    border:1px solid #1f2937;
    box-shadow:0 0 10px rgba(0,0,0,0.4);
}

.metric-green {color:#22c55e;}
.metric-red {color:#ef4444;}
</style>
""", unsafe_allow_html=True)

# =========================
# 🔝 HEADER
# =========================
col1, col2, col3 = st.columns([2,4,2])

with col1:
    st.markdown("## 🔥 SHREE AI")

with col2:
    symbol = st.text_input("🔍 Search Symbol", value="NIFTY").upper()

with col3:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.metric("💰 Balance", "₹1,00,000")
    st.metric("📊 P&L", "+₹2,500")
    st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# =========================
# 🌍 MARKET STRIP (🔥 UPGRADE)
# =========================
def market_card(title, value, change):
    color = "#22c55e" if "+" in change else "#ef4444"

    st.markdown(f"""
    <div class="card">
        <h4 style="color:#9ca3af;">{title}</h4>
        <h2>{value}</h2>
        <span style="color:{color};font-weight:bold;">{change}</span>
    </div>
    """, unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    market_card("🇮🇳 NIFTY", "22,450", "+120")
    market_card("BANKNIFTY", "48,200", "+300")

with col2:
    market_card("🌎 DOW", "38,500", "+200")
    market_card("NASDAQ", "16,200", "+100")

with col3:
    market_card("🛢️ GOLD", "62,000", "+500")
    market_card("CRUDE", "6,500", "-100")

st.divider()

if not symbol:
    st.stop()

# =========================
# 🚀 FETCH DATA
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
# 🔌 WS START
# =========================
if "ws_started" not in st.session_state:
    try:
        start_live_feed()
        start_depth_feed()
        st.session_state.ws_started = True
    except:
        pass

# =========================
# 📡 SUBSCRIBE
# =========================
if "subscribed_symbol" not in st.session_state or st.session_state.subscribed_symbol != symbol:
    try:
        subscribe_instrument(data["security_id"], data["segment"])
        subscribe_depth(data["security_id"], data["segment"])
        st.session_state.subscribed_symbol = symbol
    except:
        pass

# =========================
# 💰 LIVE PRICE
# =========================
live_price = get_live_ltp()
spot = live_price if live_price != 0 else data.get("ltp", 0)

# =========================
# 🔀 TABS
# =========================
tab1, tab2, tab3 = st.tabs(["📊 Option", "📈 Stock", "🧠 War Room"])

# ============================================================
# 📊 OPTION DASHBOARD
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

            rows = []

            if option_data and "data" in option_data:
                oc = option_data["data"].get("oc", {})

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

                if "limit" not in st.session_state:
                    st.session_state.limit = 10

                if st.button("➕ Load More"):
                    st.session_state.limit += 10

                st.dataframe(df.head(st.session_state.limit), use_container_width=True)

        except Exception as e:
            st.error(f"Option Error: {e}")

# ============================================================
# 📈 STOCK DASHBOARD
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
            df = pd.DataFrame(hist)

            fig = go.Figure(data=[go.Candlestick(
                x=df["time"],
                open=df["open"],
                high=df["high"],
                low=df["low"],
                close=df["close"]
            )])

            fig.update_layout(template="plotly_dark")

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No chart data")

# ============================================================
# 🧠 WAR ROOM (🔥 POWER MODE)
# ============================================================
with tab3:

    st.markdown("## 🧠 War Room")

    cols = st.slider("Columns", 1, 4, 2)
    grid = st.columns(cols)

    panels = [
        "NIFTY",
        "BANKNIFTY",
        "OI",
        "FII/DII",
        "Depth",
        "AI"
    ]

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

# =========================
# 🔍 DEBUG
# =========================
with st.expander("Debug"):
    st.json(data)
