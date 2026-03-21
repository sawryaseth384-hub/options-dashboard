import streamlit as st
from streamlit_autorefresh import st_autorefresh
import sys, os, time
import pandas as pd

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

# Optional modules
optional_modules = {}

try:
    from dhan_data.live_market_feed import start_live_feed, get_live_ltp, subscribe_instrument
    optional_modules['live_feed'] = (start_live_feed, get_live_ltp, subscribe_instrument)
except:
    optional_modules['live_feed'] = None

try:
    from dhan_data.market_quote import get_ltp
    optional_modules['market_quote'] = get_ltp
except:
    optional_modules['market_quote'] = None


# =========================
# 🔥 PAGE
# =========================
st.set_page_config(layout="wide")
st.title("📈 Dhan AI Options Dashboard")

# =========================
# 🚀 START WS
# =========================
if "init_done" not in st.session_state:
    if optional_modules['live_feed']:
        start_live_feed, _, _ = optional_modules['live_feed']
        start_live_feed()

    st.session_state.init_done = True
    st.session_state.ws_start_time = time.time()

# =========================
# 🔁 AUTO REFRESH
# =========================
st_autorefresh(interval=5000, key="refresh")

# =========================
# 📊 INSTRUMENT SELECT
# =========================
instrument = st.selectbox("Select Instrument", ["NIFTY", "BANKNIFTY"])

if instrument == "NIFTY":
    security_id = 13
else:
    security_id = 25

segment = "IDX_I"

# =========================
# 📡 SUBSCRIBE
# =========================
if "last_symbol" not in st.session_state:
    st.session_state.last_symbol = None

if optional_modules['live_feed']:
    _, _, subscribe = optional_modules['live_feed']

    if st.session_state.last_symbol != security_id:
        subscribe(security_id, segment)
        st.session_state.last_symbol = security_id

# =========================
# 💰 LIVE PRICE
# =========================
def get_spot():
    # WebSocket
    if optional_modules['live_feed']:
        _, get_live, _ = optional_modules['live_feed']
        price = get_live()

        if price and price != 0:
            return round(price, 2)

    # fallback REST
    if optional_modules['market_quote']:
        return optional_modules['market_quote'](security_id, segment)

    return 0


spot = get_spot()

# =========================
# 📅 EXPIRY
# =========================
expiries = dhan_api.get_valid_expiries(security_id)

if not expiries:
    st.warning("No expiry data (market closed or API issue)")
    st.stop()

selected_expiry = st.selectbox("Select Expiry", expiries)

# =========================
# 📊 OPTION CHAIN
# =========================
df = None

raw = dhan_api.get_option_chain(security_id, segment, selected_expiry)

if raw and raw.get("status") == "success":
    df, _ = helpers.process_option_data(raw)
else:
    st.warning("Option Chain not available")

# =========================
# 📊 METRICS
# =========================
col1, col2, col3, col4 = st.columns(4)

if df is not None and not df.empty:
    pcr = helpers.calculate_pcr(df)
    support, resistance = helpers.get_support_resistance(df)
else:
    pcr = support = resistance = 0

col1.metric("Spot", spot if spot else "Waiting...")
col2.metric("PCR", round(pcr, 2) if pcr else "N/A")
col3.metric("Support", support if support else "N/A")
col4.metric("Resistance", resistance if resistance else "N/A")

# =========================
# 📋 TABLE
# =========================
if df is not None and not df.empty:
    st.dataframe(df, use_container_width=True)

# =========================
# 🚀 SIGNAL
# =========================
if df is not None and not df.empty:
    if pcr < 0.8:
        st.success("🟢 Bullish")
    elif pcr > 1.2:
        st.error("🔴 Bearish")
    else:
        st.warning("🟡 Neutral")
else:
    st.warning("No Data")
