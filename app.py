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
# 🔄 SEGMENT MAP (FIXED)
# =========================
def map_segment(symbol):
    symbol = symbol.upper()

    if "NIFTY" in symbol:
        return "IDX_I"

    elif "BANKNIFTY" in symbol:
        return "IDX_I"

    return "NSE_EQ"


mapped_segment = map_segment(selected_symbol)


# =========================
# 📡 SUBSCRIBE LIVE (SAFE)
# =========================
if "last_symbol" not in st.session_state:
    st.session_state.last_symbol = None

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

    symbol = selected_symbol.upper()

    if "BANKNIFTY" in symbol:
        return get_ltp(25, "IDX_I")

    elif "NIFTY" in symbol:
        return get_ltp(13, "IDX_I")

    return get_ltp(security_id, segment)


spot = get_spot()


# =========================
# 📅 EXPIRY LIST (FIXED)
# =========================
expiry_list = dhan_api.get_valid_expiries(security_id, mapped_segment)

selected_expiry = None
if expiry_list:
    selected_expiry = st.selectbox("Select Expiry", expiry_list)


# =========================
# 📊 OPTION CHAIN (FINAL FIX)
# =========================
df = None

if selected_expiry:

    # 🔥 IMPORTANT: INDEX vs STOCK handling
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
        st.warning("⚠️ Option Chain not available (Rate limit / Wrong segment)")


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
# =========================
# 📁 FILE / MODULE HEALTH CHECK
# =========================
st.markdown("## 📁 FILE HEALTH CHECK")

with st.expander("🔍 Check All Modules", expanded=True):

    results = {}

    # -------------------------
    # core.dhan_api
    # -------------------------
    try:
        from core import dhan_api
        results["core/dhan_api.py"] = "✅ Imported"
    except Exception as e:
        results["core/dhan_api.py"] = f"❌ {e}"

    # -------------------------
    # utils.helpers
    # -------------------------
    try:
        from utils import helpers
        results["utils/helpers.py"] = "✅ Imported"
    except Exception as e:
        results["utils/helpers.py"] = f"❌ {e}"

    # -------------------------
    # instruments
    # -------------------------
    try:
        from dhan_data import instruments
        df_test = instruments.get_instrument_df()
        if df_test is not None and not df_test.empty:
            results["dhan_data/instruments.py"] = "✅ Working"
        else:
            results["dhan_data/instruments.py"] = "❌ Empty Data"
    except Exception as e:
        results["dhan_data/instruments.py"] = f"❌ {e}"

    # -------------------------
    # market_quote
    # -------------------------
    try:
        from dhan_data.market_quote import get_ltp
        test_price = get_ltp(13, "IDX_I")
        if test_price:
            results["dhan_data/market_quote.py"] = "✅ Working"
        else:
            results["dhan_data/market_quote.py"] = "❌ No Data"
    except Exception as e:
        results["dhan_data/market_quote.py"] = f"❌ {e}"

    # -------------------------
    # live_market_feed
    # -------------------------
    try:
        from dhan_data.live_market_feed import get_live_ltp
        live = get_live_ltp()
        if live:
            results["dhan_data/live_market_feed.py"] = "✅ Working"
        else:
            results["dhan_data/live_market_feed.py"] = "⚠️ No Live Data"
    except Exception as e:
        results["dhan_data/live_market_feed.py"] = f"❌ {e}"

    # -------------------------
    # depth_feed
    # -------------------------
    try:
        from dhan_data.depth_feed import get_depth
        depth = get_depth()
        if depth:
            results["dhan_data/depth_feed.py"] = "✅ Working"
        else:
            results["dhan_data/depth_feed.py"] = "⚠️ No Data"
    except Exception as e:
        results["dhan_data/depth_feed.py"] = f"❌ {e}"

    # -------------------------
    # chart
    # -------------------------
    try:
        from dhan_data import chart
        cdf = chart.get_candle_data(13, "IDX_I")
        if cdf is not None and not cdf.empty:
            results["dhan_data/chart.py"] = "✅ Working"
        else:
            results["dhan_data/chart.py"] = "❌ No Data"
    except Exception as e:
        results["dhan_data/chart.py"] = f"❌ {e}"

    # -------------------------
    # helpers processing
    # -------------------------
    try:
        if df is not None:
            _ = helpers.calculate_pcr(df)
            results["utils/helpers (logic)"] = "✅ Working"
        else:
            results["utils/helpers (logic)"] = "⚠️ No Data"
    except Exception as e:
        results["utils/helpers (logic)"] = f"❌ {e}"

    # -------------------------
    # SHOW RESULTS
    # -------------------------
    for file, status in results.items():
        st.write(f"{file} → {status}")
