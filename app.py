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
# 📦 IMPORTS (with fallbacks)
# =========================
try:
    from core import dhan_api
except ImportError as e:
    st.error(f"❌ Failed to import core.dhan_api: {e}")
    st.stop()

try:
    from utils import helpers
except ImportError as e:
    st.error(f"❌ Failed to import utils.helpers: {e}")
    st.stop()

# Optional imports – if missing, we disable those features
optional_modules = {}

try:
    from utils.debug import render_debug_panel
    optional_modules['debug'] = render_debug_panel
except ImportError:
    optional_modules['debug'] = None

try:
    from dhan_data import instruments
    optional_modules['instruments'] = instruments
except ImportError:
    optional_modules['instruments'] = None

try:
    from dhan_data import chart
    optional_modules['chart'] = chart
except ImportError:
    optional_modules['chart'] = None

try:
    from dhan_data.market_quote import get_ltp as market_quote_ltp
    optional_modules['market_quote'] = market_quote_ltp
except ImportError:
    optional_modules['market_quote'] = None

try:
    from dhan_data.live_market_feed import (
        start_live_feed,
        get_live_ltp,
        subscribe_instrument
    )
    optional_modules['live_feed'] = (start_live_feed, get_live_ltp, subscribe_instrument)
except ImportError:
    optional_modules['live_feed'] = None

try:
    from dhan_data.depth_feed import start_depth_feed, get_depth
    optional_modules['depth'] = (start_depth_feed, get_depth)
except ImportError:
    optional_modules['depth'] = None

# =========================
# 🔥 PAGE CONFIG
# =========================
st.set_page_config(page_title="Dhan AI Options Dashboard", layout="wide")
st.title("📈 Dhan AI Options Dashboard")

# =========================
# 🚀 WEBSOCKET START (if available)
# =========================
if "init_done" not in st.session_state:
    if optional_modules['live_feed']:
        start_live_feed, _, _ = optional_modules['live_feed']
        start_live_feed()
    if optional_modules['depth']:
        start_depth_feed, _ = optional_modules['depth']
        start_depth_feed()
    st.session_state.init_done = True
    st.session_state.ws_start_time = time.time()
else:
    # if modules not available, just set dummy values to avoid errors
    if 'ws_start_time' not in st.session_state:
        st.session_state.ws_start_time = time.time()

# =========================
# 🔁 AUTO REFRESH
# =========================
st_autorefresh(interval=15000, key="live")

# =========================
# 📊 SELECT INSTRUMENT (with fallback)
# =========================
if optional_modules['instruments']:
    df_instr = optional_modules['instruments'].get_instrument_df()
    if df_instr is not None and not df_instr.empty:
        selected_symbol = st.selectbox(
            "Select Instrument",
            sorted(df_instr["SEM_TRADING_SYMBOL"].unique())
        )
        row = df_instr[df_instr["SEM_TRADING_SYMBOL"] == selected_symbol].iloc[0]
        security_id = int(row["SEM_SMST_SECURITY_ID"])
        segment = row["SEM_SEGMENT"]
        st.success(f"✅ {selected_symbol}")
        st.caption(f"Security ID: {security_id} | Segment: {segment}")
    else:
        st.warning("⚠️ Instrument list empty or unavailable. Using default NIFTY.")
        selected_symbol = "NIFTY 50"
        security_id = 13
        segment = "IDX_I"
else:
    st.warning("⚠️ dhan_data/instruments not available. Using default NIFTY.")
    selected_symbol = "NIFTY 50"
    security_id = 13
    segment = "IDX_I"

# =========================
# 🔄 SEGMENT MAP (for live subscription)
# =========================
def map_segment(symbol):
    symbol = symbol.upper()
    if "NIFTY" in symbol or "BANKNIFTY" in symbol:
        return "IDX_I"
    return "NSE_EQ"

mapped_segment = map_segment(selected_symbol)

# =========================
# 📡 SUBSCRIBE LIVE (if available)
# =========================
if "last_symbol" not in st.session_state:
    st.session_state.last_symbol = None

ws_ready = (time.time() - st.session_state.ws_start_time) > 2

if ws_ready and st.session_state.last_symbol != security_id and optional_modules['live_feed']:
    _, _, subscribe = optional_modules['live_feed']
    subscribe_instrument(security_id, mapped_segment)
    st.session_state.last_symbol = security_id

# =========================
# 💰 GET LIVE SPOT
# =========================
def get_spot():
    # Try WebSocket first
    if optional_modules['live_feed']:
        _, get_live, _ = optional_modules['live_feed']
        price = get_live()
        if price and price != 0:
            return round(price, 2)

    # Fallback to market quote
    if optional_modules['market_quote']:
        symbol = selected_symbol.upper()
        if "BANKNIFTY" in symbol:
            return optional_modules['market_quote'](25, "IDX_I")
        elif "NIFTY" in symbol:
            return optional_modules['market_quote'](13, "IDX_I")
        else:
            return optional_modules['market_quote'](security_id, segment)

    # Ultimate fallback: try our own get_ltp from core.dhan_api
    try:
        return dhan_api.get_ltp(security_id, segment)  # we added this in core
    except:
        return None

spot = get_spot()
if spot is None:
    spot = 0

# =========================
# 📅 EXPIRY LIST (using our core function)
# =========================
expiry_list = dhan_api.get_valid_expiries(security_id)   # signature: get_valid_expiries(security_id)

selected_expiry = None
if expiry_list:
    selected_expiry = st.selectbox("Select Expiry", expiry_list)

# =========================
# 📊 OPTION CHAIN
# =========================
df = None

if selected_expiry:
    # Determine correct segment for options
    if mapped_segment == "IDX_I":
        option_segment = "IDX_I"
    else:
        option_segment = "NSE_FNO"

    raw = dhan_api.get_option_chain(
        security_id,
        option_segment,
        selected_expiry
    )

    if raw and raw.get("status") == "success" and "data" in raw:
        df, _ = helpers.process_option_data(raw)
    else:
        st.warning("⚠️ Option Chain not available (Rate limit / Wrong segment / Expiry invalid)")

# =========================
# 📊 METRICS
# =========================
col1, col2, col3, col4, col5 = st.columns(5)

if df is not None and not df.empty:
    pcr = helpers.calculate_pcr(df)
    support, resistance = helpers.get_support_resistance(df)
    atm = helpers.get_atm_strike(df, spot)
else:
    pcr = support = resistance = atm = 0

col1.metric("Spot", spot if spot else "N/A")
col2.metric("PCR", round(pcr, 2) if pcr else "N/A")
col3.metric("Support", support if support else "N/A")
col4.metric("Resistance", resistance if resistance else "N/A")
col5.metric("ATM", atm if atm else "N/A")

# =========================
# 🚀 SIGNAL
# =========================
if df is not None and not df.empty:
    signal = helpers.get_signal(pcr)
else:
    signal = "🟡 Neutral – No data"
st.subheader(f"Signal: {signal}")

# =========================
# 📋 OPTION TABLE
# =========================
if df is not None and not df.empty:
    st.dataframe(df, use_container_width=True)

# =========================
# 📊 CHARTS (optional helpers)
# =========================
if df is not None and not df.empty:
    try:
        # These functions may not exist; we wrap in try/except
        if hasattr(helpers, 'plot_oi_heatmap'):
            st.plotly_chart(helpers.plot_oi_heatmap(df), use_container_width=True)
        if hasattr(helpers, 'plot_payoff'):
            st.plotly_chart(helpers.plot_payoff(atm), use_container_width=True)
    except Exception as e:
        st.info(f"Chart rendering skipped: {e}")

# =========================
# 📈 PRICE CHART (optional)
# =========================
st.markdown("## Price Chart")
if optional_modules['chart']:
    chart_df = optional_modules['chart'].get_candle_data(security_id, mapped_segment)
    if chart_df is not None and not chart_df.empty:
        fig, trend = optional_modules['chart'].plot_candle(chart_df)
        st.plotly_chart(fig, use_container_width=True)
        st.success(f"Trend: {trend}")
    else:
        st.warning("No chart data")
else:
    st.info("Chart module not available. Install dhan_data.chart to see price charts.")

# =========================
# 📊 MARKET DEPTH (optional)
# =========================
st.markdown("## Market Depth")
if optional_modules['depth']:
    _, get_depth = optional_modules['depth']
    depth = get_depth()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Bids")
        st.dataframe(depth.get("bids", []), use_container_width=True)
    with col2:
        st.subheader("Asks")
        st.dataframe(depth.get("asks", []), use_container_width=True)
else:
    st.info("Depth feed module not available.")

# =========================
# 📁 FILE / MODULE HEALTH CHECK (simple version)
# =========================
st.markdown("## 📁 FILE HEALTH CHECK")
with st.expander("🔍 Check Core Modules", expanded=False):
    core_status = {}
    try:
        from core import dhan_api
        core_status["core/dhan_api.py"] = "✅ Imported"
    except Exception as e:
        core_status["core/dhan_api.py"] = f"❌ {e}"

    try:
        from utils import helpers
        core_status["utils/helpers.py"] = "✅ Imported"
    except Exception as e:
        core_status["utils/helpers.py"] = f"❌ {e}"

    for name, status in core_status.items():
        st.write(f"{name} → {status}")

# =========================
# 🤖 SYSTEM SELF DIAGNOSIS (simplified)
# =========================
st.markdown("## 🤖 SYSTEM SELF DIAGNOSIS")
with st.expander("🔍 Run Full Diagnosis", expanded=False):
    def safe_check(name, func):
        try:
            result = func()
            if result is None:
                return f"{name} → ⚠️ No Data"
            elif result is False:
                return f"{name} → ❌ Failed"
            else:
                return f"{name} → ✅ Working"
        except Exception as e:
            return f"{name} → ❌ Error: {str(e)}"

    results = []
    # Check expiry API
    results.append(safe_check(
        "expiry API",
        lambda: dhan_api.get_valid_expiries(security_id)
    ))
    # Check option chain API (if expiry selected)
    if selected_expiry:
        results.append(safe_check(
            "option_chain API",
            lambda: dhan_api.get_option_chain(security_id, option_segment, selected_expiry)
        ))
    # Check helpers (if df exists)
    if df is not None:
        results.append(safe_check(
            "helpers processing",
            lambda: helpers.calculate_pcr(df)
        ))
    for r in results:
        st.write(r)

# =========================
# 🛠 DEBUG (if available)
# =========================
if optional_modules['debug']:
    optional_modules['debug']()
