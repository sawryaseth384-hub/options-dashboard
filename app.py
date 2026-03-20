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

st.set_page_config(page_title="Dhan AI Options Dashboard", layout="wide")
st.title("📈 Dhan AI Options Dashboard")


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
# 🔁 AUTO REFRESH
# =========================
refresh = st.selectbox("Auto Refresh (seconds)", [0, 5, 10, 30])
if refresh > 0:
    st_autorefresh(interval=refresh * 1000, key="refresh")


# =========================
# 🔥 SEGMENT MAP
# =========================
def get_segment(seg):
    if seg == "D":
        return "NSE_FNO"
    else:
        return "IDX_I"


mapped_segment = get_segment(segment)


# =========================
# 🔥 EXPIRY
# =========================
expiry_list = dhan_api.get_valid_expiries(security_id, mapped_segment)

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
spot = 0

if raw_data and raw_data.get("status") == "success":
    df, spot = helpers.process_option_data(raw_data)


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
col2.metric("PCR", pcr)
col3.metric("Support", support)
col4.metric("Resistance", resistance)
col5.metric("ATM", atm)


# =========================
# 🚀 SIGNAL
# =========================
signal = helpers.get_signal(pcr)
st.subheader(f"🚀 Signal: {signal}")


# =========================
# 📊 TABLE
# =========================
if df is not None:
    st.dataframe(df, width="stretch")


# =========================
# 📊 CHART
# =========================
if df is not None:
    st.plotly_chart(helpers.plot_oi_heatmap(df), width="stretch")
    st.plotly_chart(helpers.plot_payoff(atm), width="stretch")


# =========================
# DEBUG
# =========================
render_debug_panel()
