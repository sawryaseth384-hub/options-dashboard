import streamlit as st
from streamlit_autorefresh import st_autorefresh

import sys, os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from core import dhan_api
from utils import helpers
from utils.debug import render_debug_panel
from dhan_data import instruments


st.set_page_config(page_title="Dhan AI Options Dashboard", layout="wide")
st.title("📈 Dhan AI Options Dashboard")


# =========================
# 🔥 INSTRUMENT SELECT
# =========================
df_instr = instruments.get_instrument_df()

# 🔥 Remove non F&O equity (extra safety)
df_instr = df_instr[
    (df_instr["SEM_SEGMENT"] == "D") | (df_instr["SEM_SEGMENT"] == "I")
]

selected_symbol = st.selectbox(
    "Select Instrument",
    sorted(df_instr["SEM_TRADING_SYMBOL"].unique())
)

selected_row = df_instr[df_instr["SEM_TRADING_SYMBOL"] == selected_symbol].iloc[0]

security_id = int(selected_row["SEM_SMST_SECURITY_ID"])
segment = selected_row["SEM_SEGMENT"]

st.success(f"✅ Selected: {selected_symbol}")
st.caption(f"Security ID: {security_id} | Segment: {segment}")


# =========================
# 🔁 AUTO REFRESH
# =========================
refresh = st.selectbox("Auto Refresh (seconds)", [0, 5, 10, 30])
if refresh > 0:
    st_autorefresh(interval=refresh * 1000, key="refresh")


# =========================
# 🔥 SEGMENT MAPPING
# =========================
def get_segment(seg):
    if seg == "D":
        return "NSE_FNO"
    elif seg == "E":
        return "NSE_EQ"
    else:
        return "IDX_I"


mapped_segment = get_segment(segment)


# =========================
# 🔥 EXPIRY FETCH
# =========================
expiry_list = []

try:
    expiry_list = dhan_api.get_valid_expiries(
        security_id,
        mapped_segment
    )

    st.write("DEBUG Expiry:", expiry_list)  # 🔥 debug

except Exception as e:
    st.error(f"❌ Expiry Error: {e}")


selected_expiry = None

if expiry_list:
    selected_expiry = st.selectbox("Select Expiry", expiry_list)
else:
    st.warning("⚠️ No expiry available (check instrument)")


# =========================
# 🔥 OPTION CHAIN FETCH
# =========================
raw_data = None

try:
    if selected_expiry:
        raw_data = dhan_api.get_option_chain(
            security_id,
            mapped_segment,
            selected_expiry
        )

        st.write("DEBUG API:", raw_data)  # 🔥 debug

except Exception as e:
    st.error(f"❌ Option Chain Error: {e}")


# =========================
# 🔥 PROCESS DATA
# =========================
df = None
spot = 0

try:
    if raw_data and raw_data.get("status") == "success":
        df, spot = helpers.process_option_data(raw_data)
    else:
        st.warning("⚠️ Invalid API data")

except Exception as e:
    st.error(f"❌ Processing Error: {e}")


# =========================
# 📊 METRICS
# =========================
col1, col2, col3, col4, col5 = st.columns(5)

pcr, support, resistance, atm = 0, 0, 0, 0

try:
    if df is not None and not df.empty:
        pcr = helpers.calculate_pcr(df)
        support, resistance = helpers.get_support_resistance(df)
        atm = helpers.get_atm_strike(df, spot)
except Exception as e:
    st.error(f"❌ Metrics Error: {e}")

col1.metric("📊 Spot", spot)
col2.metric("📊 PCR", pcr)
col3.metric("🟢 Support", support)
col4.metric("🔴 Resistance", resistance)
col5.metric("🎯 ATM", atm)


# =========================
# 🚀 SIGNAL
# =========================
signal = "N/A"

try:
    signal = helpers.get_signal(pcr)
except Exception as e:
    st.error(f"❌ Signal Error: {e}")

st.subheader(f"🚀 Market Signal: {signal}")


# =========================
# 📊 TABLE
# =========================
if df is not None and not df.empty:
    try:
        styled_df = df.style.apply(lambda row: helpers.highlight_atm(row, atm), axis=1)
        st.dataframe(styled_df, use_container_width=True)
    except Exception as e:
        st.error(f"❌ Table Error: {e}")
else:
    st.warning("⚠️ No data available")


# =========================
# 🚀 ADVANCED PANEL
# =========================
st.markdown("## 🚀 Advanced Panel")

try:
    prev_df = st.session_state.get("prev_df", None)

    if df is not None:
        df = helpers.calculate_oi_change(df, prev_df)
        st.session_state["prev_df"] = df.copy()

    st.success("✅ OI Change Working")

except Exception as e:
    st.error(f"❌ OI Change Error: {e}")


# DOMINANCE
try:
    dominance = helpers.get_dominance(pcr)
    st.info(f"📊 Dominance: {dominance}")
except Exception as e:
    st.error(f"❌ Dominance Error: {e}")


# TREND
try:
    trend = helpers.get_trend(df)
    st.info(f"📈 Trend: {trend}")
except Exception as e:
    st.error(f"❌ Trend Error: {e}")


# AI SIGNAL
try:
    ai = helpers.ai_signal(pcr, trend)
    st.success(f"🤖 AI Signal: {ai}")
except Exception as e:
    st.error(f"❌ AI Error: {e}")


# STRATEGY
try:
    strategy = helpers.build_strategy(signal, atm)
    st.info(f"💰 Strategy: {strategy}")
except Exception as e:
    st.error(f"❌ Strategy Error: {e}")


# =========================
# 📊 CHARTS
# =========================
try:
    if df is not None:
        st.plotly_chart(helpers.plot_oi_heatmap(df), use_container_width=True)
except Exception as e:
    st.error(f"❌ Heatmap Error: {e}")

try:
    st.plotly_chart(helpers.plot_payoff(atm), use_container_width=True)
except Exception as e:
    st.error(f"❌ Payoff Error: {e}")


# =========================
# 🔧 DEBUG PANEL
# =========================
render_debug_panel()
