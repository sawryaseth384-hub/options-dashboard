import streamlit as st
import pandas as pd

def show_stocks():

    st.subheader("📊 Stocks")

    col1, col2 = st.columns([3, 1])

    with col1:
        df = pd.DataFrame({
            "Stock": ["RELIANCE", "TCS", "INFY"],
            "Price": [2500, 3500, 1500],
            "Change": ["+10", "-20", "+15"]
        })

        st.dataframe(df, use_container_width=True)

    with col2:
        st.markdown("### ⚙️ Filters")
        st.selectbox("Stock", ["RELIANCE", "TCS", "INFY"])
        st.button("Apply")
