import streamlit as st
from streamlit_autorefresh import st_autorefresh
import sys, os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from core import dhan_api
from utils import helpers
from utils.debug import render_debug_panel
from dhan_data import instruments
from dhan_data import chart
from dhan_data.market_quote import get_ltp
from dhan_data.depth_feed import start_depth_feed, get_depth

# ✅ NEW IMPORT
from dhan_data.live_feed import start_live_feed, get_live_ltp


# =========================
# 🔥 PAGE CONFIG
# =========================
st.set_page_config(page_title="Dhan AI Options Dashboard", layout="wide")
st.title("📈 Dhan AI Options Dashboard")


# =========================
# 🔥 START LIVE FEED (ONCE)
# =========================
if "ws_started" not in st.session_state:
    start_live_feed()
    st.session_state.ws_started = True


# =========================
# 🔁 AUTO REFRESH
# =========================
st_autorefresh(interval=2000, key="live")   # fast refresh


# =========================
# 🔥 INSTRUMENT SELECT
# =========================
df_instr = instruments.get_instrument_df()

selected_symbol = st.selectbox(
    "Select Instrument",
    sorted(df_instr["SEM_TRADING_SYMBOL"].unique())
)

row = df_instr[df_instr["SEM_TRADING_SYMBOL"] == selected_symbol].iloc[0]

security_id = int(row["SEM_SMST_SECURITY_ID"])
segment = row["SEM_SEGMENT"]

st.success(f"✅ Selected: {selected_symbol}")
st.caption(f"Security ID: {security_id} | Segment: {segment}")


# =========================
# 🔥 SEGMENT MAP
# =========================
def map_segment(seg):
    if seg == "D":
        return "NSE_FNO"
    else:
        return "NSE_EQ"


mapped_segment = map_segment(segment)


# =========================
# 🔥 🚀 LIVE SPOT PRICE (FINAL)
# =========================
live_price = get_live_ltp()

if live_price and live_price != 0:
    spot = live_price
else:
    # fallback (if websocket not ready)
    symbol = selected_symbol.upper()

    if "BANKNIFTY" in symbol:
        spot = get_ltp(25, "IDX_I")

    elif "NIFTY" in symbol:
        spot = get_ltp(13, "IDX_I")

    else:
        spot = get_ltp(security_id, segment)


# =========================
# 🔥 EXPIRY
# =========================
expiry_list = []

try:
    expiry_list = dhan_api.get_valid_expiries(security_id, mapped_segment)
except Exception as e:
    st.error(f"Expiry Error: {e}")

selected_expiry = None

if expiry_list:
    selected_expiry = st.selectbox("Select Expiry", expiry_list)
else:
    st.warning("⚠️ No expiry available")


# =========================
# 🔥 OPTION CHAIN
# =========================
raw_data = None

if selected_expiry:
    raw_data = dhan_api.get_option_chain(
        security_id,
        mapped_segment,
        selected_expiry
    )


# =========================
# 🔥 PROCESS DATA
# =========================
df = None

if raw_data and raw_data.get("status") == "success":
    df, _ = helpers.process_option_data(raw_data)
else:
    st.error("❌ Option Chain Failed")


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

col1.metric("📊 Spot", spot)
col2.metric("📊 PCR", round(pcr, 2))
col3.metric("🟢 Support", support)
col4.metric("🔴 Resistance", resistance)
col5.metric("🎯 ATM", atm)


# =========================
# 🚀 SIGNAL
# =========================
signal = helpers.get_signal(pcr)
st.subheader(f"🚀 Signal: {signal}")


# =========================
# 📊 OPTION TABLE
# =========================
if df is not None:
    st.dataframe(df, use_container_width=True)


# =========================
# 📊 OPTION CHARTS
# =========================
if df is not None:
    st.plotly_chart(helpers.plot_oi_heatmap(df), use_container_width=True)
    st.plotly_chart(helpers.plot_payoff(atm), use_container_width=True)


# =========================
# 📈 LIVE CANDLE CHART
# =========================
st.markdown("## 📈 Live Chart")

chart_df = chart.get_candle_data(security_id, segment)

if chart_df is not None and not chart_df.empty:
    fig, trend = chart.plot_candle(chart_df)
    st.plotly_chart(fig, use_container_width=True)
    st.success(f"📈 Trend: {trend}")
else:
    st.warning("⚠️ No chart data")


# =========================
# DEBUG
# =========================
render_debug_panel()
