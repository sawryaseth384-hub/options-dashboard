import streamlit as st

def show_stocks(data):

    st.markdown("## 📊 Stocks Overview")

    # ===== SIMPLE GRID =====
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="NIFTY",
            value=data["NIFTY"]["ltp"],
            delta=data["NIFTY"]["change"]
        )

    with col2:
        st.metric(
            label="BANKNIFTY",
            value=data["BANKNIFTY"]["ltp"],
            delta=data["BANKNIFTY"]["change"]
        )

    with col3:
        st.metric(
            label="SENSEX",
            value=data["SENSEX"]["ltp"],
            delta=data["SENSEX"]["change"]
        )

    st.divider()

    # ===== EXTRA STOCKS TABLE (OPTIONAL) =====
    st.markdown("### 📋 Top Stocks")

    sample_data = [
        {"Stock": "RELIANCE", "Price": 2500, "Change": "+10"},
        {"Stock": "TCS", "Price": 3800, "Change": "-20"},
        {"Stock": "INFY", "Price": 1500, "Change": "+15"},
    ]

    st.dataframe(sample_data, use_container_width=True)
