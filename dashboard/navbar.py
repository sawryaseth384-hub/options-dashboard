import streamlit as st

def show_navbar():
    return st.radio("", ["Stocks", "Options", "Futures"], horizontal=True)
