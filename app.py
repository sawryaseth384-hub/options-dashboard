import streamlit as st
from streamlit_autorefresh import st_autorefresh

from core.api import fetch_data
from core.processor import process_data
from components.navbar import render_navbar
from components.watchlist import render_watchlist
from components.table import render_table

# 🔄 Auto refresh
st_autorefresh(interval=3000, key="refresh")

st.set_page_config(layout="wide")

st.title("📊 DHAN PRO DASHBOARD")

# 🔥 FETCH
data = fetch_data()
rows = process_data(data)

# 🔥 NAVBAR
tab1, tab2, tab3, tab4, tab5 = render_navbar()

# 🔥 LAYOUT
left, right = st.columns([1, 3])

with left:
    render_watchlist(rows)

with right:
    with tab1:
        render_table(rows)

    with tab2:
        stock = [r for r in rows if "NSE_EQ" in r["Symbol"]]
        render_table(stock)

    with tab3:
        opt = [r for r in rows if "NSE_FNO" in r["Symbol"]]
        render_table(opt)

    with tab4:
        st.write("Futures Coming Soon")

    with tab5:
        st.metric("NIFTY", "23,700", "+120")
