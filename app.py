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

# 🔥 EXPIRY
expiry_list = get_expiry_list()

selected_expiry = st.selectbox("Select Expiry", expiry_list)

# 🔥 OPTION CHAIN
raw_data = get_option_chain(selected_expiry)

data = process_option_data(raw_data)

# 🔥 METRICS
show_metrics(data)

# 🔥 CHART
show_oi_chart(data)

# 🔥 TABLE
show_option_table(data)
