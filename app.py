import streamlit as st
from streamlit_autorefresh import st_autorefresh

import sys, os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from core import dhan_api
from utils import helpers
from utils.debug import render_debug_panel

st.set_page_config(page_title="Dhan AI Options Dashboard", layout="wide")
st.title("📈 Dhan AI Options Dashboard")

# 🔁 Auto Refresh
refresh = st.selectbox("Auto Refresh (seconds)", [0, 5, 10, 30])
if refresh > 0:
    st_autorefresh(interval=refresh * 1000, key="refresh")

# =========================
# EXPIRY
# =========================
expiry_list = dhan_api.get_valid_expiries()
selected_expiry = st.selectbox("Select Expiry", expiry_list) if expiry_list else None

# =========================
# DATA FETCH
# =========================
raw_data = None
if selected_expiry:
    raw_data = dhan_api.get_option_chain(selected_expiry)

df, spot = helpers.process_option_data(raw_data) if raw_data else (None, 0)

# =========================
# METRICS
# =========================
col1, col2, col3, col4, col5 = st.columns(5)

pcr = helpers.calculate_pcr(df) if df is not None else 0
support, resistance = helpers.get_support_resistance(df) if df is not None else (0, 0)
atm = helpers.get_atm_strike(df, spot) if df is not None else 0

col1.metric("Spot", spot)
col2.metric("PCR", pcr)
col3.metric("Support", support)
col4.metric("Resistance", resistance)
col5.metric("ATM", atm)

signal = helpers.get_signal(pcr)
st.subheader(f"🚀 Signal: {signal}")

# =========================
# TABLE
# =========================
if df is not None:
    styled_df = df.style.apply(lambda row: helpers.highlight_atm(row, atm), axis=1)
    st.dataframe(styled_df, use_container_width=True)

# =========================
# ADVANCED PANEL
# =========================
st.markdown("## 🚀 Advanced Panel")

if "prev_df" not in st.session_state:
    st.session_state["prev_df"] = None

df = helpers.calculate_oi_change(df, st.session_state["prev_df"])
st.session_state["prev_df"] = df.copy()

dominance = helpers.get_dominance(pcr)
trend = helpers.get_trend(df)
ai = helpers.ai_signal(pcr, trend)
strategy = helpers.build_strategy(signal, atm)

st.info(f"📊 Dominance: {dominance}")
st.info(f"📈 Trend: {trend}")
st.success(f"🤖 AI Signal: {ai}")
st.info(f"💰 Strategy: {strategy}")

# Charts
st.plotly_chart(helpers.plot_oi_heatmap(df))
st.plotly_chart(helpers.plot_payoff(atm))

# =========================
# DEBUG
# =========================
render_debug_panel()
