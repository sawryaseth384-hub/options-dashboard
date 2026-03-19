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

st.write("📆 EXPIRIES:", expiry_list)  # debug

if not expiry_list:
    st.error("❌ Expiry load failed")
    st.stop()

selected_expiry = st.selectbox("Select Expiry", expiry_list)

# 🔥 OPTION CHAIN
raw_data = get_option_chain(selected_expiry)

if not raw_data:
    st.error("❌ Option chain not received")
    st.stop()

# 🔥 PROCESS
df, spot = process_option_data(raw_data)

if df.empty:
    st.warning("⚠️ No data")
    st.stop()

# 🔥 DISPLAY
st.metric("📊 Spot Price", f"₹{spot:,.2f}")

st.dataframe(df)
