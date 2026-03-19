import streamlit as st
from streamlit_autorefresh import st_autorefresh

from core.dhan_api import get_expiry_list, get_option_chain
from utils.helpers import process_option_data

st.set_page_config(page_title="Dhan AI Options Dashboard", layout="wide")

st.title("📈 Dhan AI Options Dashboard")

# 🔁 AUTO REFRESH
refresh = st.selectbox("Auto Refresh", [0, 5, 10, 30])
if refresh:
    st_autorefresh(interval=refresh * 1000)

# 🔥 EXPIRY
expiry_list = get_expiry_list()

if not expiry_list:
    st.error("❌ Expiry load failed")
    st.stop()

selected_expiry = st.selectbox("Select Expiry", expiry_list)

# 🔥 OPTION CHAIN
raw = get_option_chain(selected_expiry)

if not raw:
    st.error("❌ Option chain failed")
    st.stop()

# 🔥 PROCESS
df, spot = process_option_data(raw)

if df.empty:
    st.warning("No data")
    st.stop()

# 🔥 SPOT
st.metric("📊 Spot Price", f"{spot}")

# 🔥 SIMPLE VIEW
st.dataframe(df, use_container_width=True)
