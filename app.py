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
st.set_page_config(page_title="🔥 AI Trading System", layout="wide")

# =========================
# 🔝 HEADER
# =========================
col1, col2, col3 = st.columns([2,4,2])

with col1:
    st.markdown("## 🔥 SHREE AI")

with col2:
    symbol = st.text_input(
        "🔍 Search Symbol",
        value="NIFTY"
    ).upper()

with col3:
    st.metric("💰 Balance", "₹1,00,000")
    st.metric("📊 P&L", "+₹2,500")

st.divider()

# =========================
# 🌍 MARKET STRIP
# =========================
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 🇮🇳 Indices")
    st.metric("NIFTY", "22,450", "+120")
    st.metric("BANKNIFTY", "48,200", "+300")

with col2:
    st.markdown("### 🌎 Global")
    st.metric("DOW", "38,500", "+200")
    st.metric("NASDAQ", "16,200", "+100")

with col3:
    st.markdown("### 🛢️ Commodity")
    st.metric("GOLD", "62,000", "+500")
    st.metric("CRUDE", "6,500", "-100")

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

    col1, col2, col3 = st.columns([3,2,2])

    col1.metric("Symbol", data.get("symbol"))
    col2.metric("Spot", spot)
    col3.metric("Segment", data.get("segment"))

    expiry = None
    if data.get("expiries"):
        expiry = st.selectbox("Expiry", data["expiries"])

    st.markdown("## 📊 Option Chain")

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

                # ✅ FIXED LOOP
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

                # 🔥 LOAD MORE
                if "limit" not in st.session_state:
                    st.session_state.limit = 10

                colA, colB = st.columns([1,1])
                with colA:
                    if st.button("➕ Load More"):
                        st.session_state.limit += 10

                st.dataframe(df.head(st.session_state.limit), use_container_width=True)

            else:
                st.warning("No option chain")

        except Exception as e:
            st.error(f"Option Error: {e}")

# ============================================================
# 📈 STOCK DASHBOARD
# ============================================================
with tab2:

    col1, col2 = st.columns([2,5])

    with col1:
        st.markdown("### Watchlist")
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

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No chart data")

# ============================================================
# 🧠 WAR ROOM (ADVANCED)
# ============================================================
with tab3:

    st.markdown("## 🧠 War Room (Custom Layout)")

    # 🔥 DYNAMIC GRID CONTROL
    cols = st.slider("Select Columns", 1, 4, 2)

    grid = st.columns(cols)

    # 🔥 PANELS (CUSTOM ADD)
    panel_options = [
        "NIFTY Chart",
        "BANKNIFTY Chart",
        "OI Analysis",
        "FII DII",
        "Market Depth",
        "AI Signals"
    ]

    selected = st.multiselect("Select Panels", panel_options, default=panel_options[:cols])

    for i, panel in enumerate(selected):
        with grid[i % cols]:

            if panel == "NIFTY Chart":
                st.subheader("NIFTY")
                st.metric("Value", spot)

            elif panel == "BANKNIFTY Chart":
                st.subheader("BANKNIFTY")
                st.metric("Value", "48,200")

            elif panel == "OI Analysis":
                st.subheader("OI")
                st.info("OI Data")

            elif panel == "FII DII":
                st.subheader("FII/DII")
                st.metric("FII", "+1200 Cr")
                st.metric("DII", "-500 Cr")

            elif panel == "Market Depth":
                depth = get_depth()
                st.dataframe(depth.get("bids", []))

            elif panel == "AI Signals":
                st.success("BUY CALL")
                st.warning("Avoid PE")

# =========================
# 🔍 DEBUG
# =========================
with st.expander("Debug"):
    st.json(data)
