import streamlit as st

def show_stocks(data):
    st.subheader("📊 Stocks")
    st.write(data["NIFTY"])
