import streamlit as st

def show_stocks(data):

    st.markdown("## 📊 Stocks")

    col1, col2, col3 = st.columns(3)

    col1.metric("NIFTY", data["NIFTY"]["ltp"], data["NIFTY"]["change"])
    col2.metric("BANKNIFTY", data["BANKNIFTY"]["ltp"], data["BANKNIFTY"]["change"])
    col3.metric("SENSEX", data["SENSEX"]["ltp"], data["SENSEX"]["change"])

    st.divider()

    st.markdown("### 📋 Watchlist")

    st.dataframe([
        {"Stock": "RELIANCE", "Price": 2500, "Change": "+10"},
        {"Stock": "TCS", "Price": 3800, "Change": "-20"},
    ], use_container_width=True)
