import streamlit as st
from streamlit_autorefresh import st_autorefresh
import sys, os, time

# =========================
# 🔧 PATH SETUP
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# =========================
# 📦 IMPORTS
# =========================
from core import dhan_api
from utils import helpers
from utils.debug import render_debug_panel
from dhan_data import instruments, chart
from dhan_data.market_quote import get_ltp
from dhan_data.live_market_feed import (
    start_live_feed,
    get_live_ltp,
    subscribe_instrument
)
from dhan_data.depth_feed import start_depth_feed, get_depth


# =========================
# 🔥 PAGE CONFIG
# =========================
st.set_page_config(page_title="Dhan AI Options Dashboard", layout="wide")
st.title("📈 Dhan AI Options Dashboard")


# =========================
# 🚀 START WEBSOCKET
# =========================
if "init_done" not in st.session_state:
    start_live_feed()
    start_depth_feed()
    st.session_state.init_done = True
    st.session_state.ws_start_time = time.time()


# =========================
# 🔁 AUTO REFRESH
# =========================
st_autorefresh(interval=3000, key="live")


# =========================
# 📊 SELECT INSTRUMENT
# =========================
df_instr = instruments.get_instrument_df()

selected_symbol = st.selectbox(
    "Select Instrument",
    sorted(df_instr["SEM_TRADING_SYMBOL"].unique())
)

row = df_instr[df_instr["SEM_TRADING_SYMBOL"] == selected_symbol].iloc[0]

security_id = int(row["SEM_SMST_SECURITY_ID"])
segment = row["SEM_SEGMENT"]

st.success(f"✅ {selected_symbol}")
st.caption(f"Security ID: {security_id} | Segment: {segment}")


# =========================
# 🔄 SEGMENT MAP
# =========================
def map_segment(symbol):
    symbol = symbol.upper()
    if "NIFTY" in symbol or "BANKNIFTY" in symbol:
        return "IDX_I"
    return "NSE_EQ"

mapped_segment = map_segment(selected_symbol)


# =========================
# 📡 SUBSCRIBE LIVE
# =========================
if "last_symbol" not in st.session_state:
    st.session_state.last_symbol = None

# wait websocket ready
ws_ready = time.time() - st.session_state.ws_start_time > 2

if ws_ready and st.session_state.last_symbol != security_id:
    subscribe_instrument(security_id, mapped_segment)
    st.session_state.last_symbol = security_id


# =========================
# 💰 GET LIVE SPOT
# =========================
def get_spot():
    price = get_live_ltp()

    if price and price != 0:
        return round(price, 2)

    # fallback API
    if "BANKNIFTY" in selected_symbol.upper():
        return get_ltp(25, "IDX_I")
    elif "NIFTY" in selected_symbol.upper():
        return get_ltp(13, "IDX_I")

    return get_ltp(security_id, segment)


spot = get_spot()


# =========================
# 📅 EXPIRY LIST
# =========================
expiry_list = dhan_api.get_valid_expiries(security_id, mapped_segment)

selected_expiry = None
if expiry_list:
    selected_expiry = st.selectbox("Select Expiry", expiry_list)


# =========================
# 📊 OPTION CHAIN
# =========================
df = None

if selected_expiry:
    raw = dhan_api.get_option_chain(
        security_id,
        "NSE_FNO",   # 🔥 IMPORTANT FIX
        selected_expiry
    )

    if raw and raw.get("status") == "success":
        df, _ = helpers.process_option_data(raw)
    else:
        st.warning("⚠️ Option Chain not available")


# =========================
# 📊 METRICS
# =========================
col1, col2, col3, col4, col5 = st.columns(5)

if df is not None:
    pcr = helpers.calculate_pcr(df)
    support, resistance = helpers.get_support_resistance(df)
    atm = helpers.get_atm_strike(df, spot)
else:
    pcr = support = resistance = atm = 0

col1.metric("Spot", spot)
col2.metric("PCR", round(pcr, 2))
col3.metric("Support", support)
col4.metric("Resistance", resistance)
col5.metric("ATM", atm)


# =========================
# 🚀 SIGNAL
# =========================
st.subheader(f"Signal: {helpers.get_signal(pcr)}")


# =========================
# 📋 OPTION TABLE
# =========================
if df is not None:
    st.dataframe(df, width="stretch")


# =========================
# 📊 CHARTS
# =========================
if df is not None:
    st.plotly_chart(helpers.plot_oi_heatmap(df), width="stretch")
    st.plotly_chart(helpers.plot_payoff(atm), width="stretch")


# =========================
# 📈 PRICE CHART
# =========================
st.markdown("## Price Chart")

chart_df = chart.get_candle_data(security_id, mapped_segment)

if chart_df is not None and not chart_df.empty:
    fig, trend = chart.plot_candle(chart_df)
    st.plotly_chart(fig, width="stretch")
    st.success(f"Trend: {trend}")
else:
    st.warning("No chart data")


# =========================
# 📊 MARKET DEPTH
# =========================
st.markdown("## Market Depth")

depth = get_depth()

col1, col2 = st.columns(2)

with col1:
    st.subheader("Bids")
    st.dataframe(depth.get("bids", []), width="stretch")

with col2:
    st.subheader("Asks")
    st.dataframe(depth.get("asks", []), width="stretch")


# =========================
# 🛠 DEBUG
# =========================
render_debug_panel()
