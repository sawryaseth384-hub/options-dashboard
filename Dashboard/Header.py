import streamlit as st

def show_header():

    st.title("📊 DHAN STYLE DASHBOARD")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("NIFTY", "23,700", "+120")

    with col2:
        st.metric("BANKNIFTY", "55,200", "+300")

    with col3:
        st.metric("GOLD", "72,000", "+100")

    with col4:
        st.metric("USD/INR", "83.10", "+0.10")

    st.divider()
