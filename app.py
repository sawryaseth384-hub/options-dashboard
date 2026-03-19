import streamlit as st
from streamlit_autorefresh import st_autorefresh

from core.dhan_api import get_expiry_list, get_option_chain
from utils.helpers import process_option_data

from dashboard.metrics import show_metrics
from dashboard.charts import show_oi_chart
from dashboard.option_table import show_option_table

st.set_page_config(page_title="Dhan AI Options Dashboard", layout="wide")

st.title("📈 Dhan AI Options Dashboard")

# 🔁 AUTO REFRESH
refresh = st.selectbox("Auto Refresh", [0, 5, 10, 30])
if refresh:
    st_autorefresh(interval=refresh * 1000)

# 🔥 EXPIRY LIST (NO STOP)
expiry_list = get_expiry_list()

# 👉 always show (fallback included)
selected_expiry = st.selectbox("Select Expiry", expiry_list)

# 🔥 OPTION CHAIN
raw_data = get_option_chain(selected_expiry)

if not raw_data:
    st.warning("⚠️ Live data not available, retrying...")
    st.stop()

# 🔥 PROCESS DATA
df, spot_price = process_option_data(raw_data)

if df.empty:
    st.warning("⚠️ No option data available")
    st.stop()

# 🔥 SPOT PRICE
st.metric("📊 Spot Price", f"₹{spot_price:,.2f}")

# 🔥 METRICS
show_metrics(df)

# 🔥 CHART
show_oi_chart(df, spot_price)

# 🔥 TABLE
show_option_table(df)
