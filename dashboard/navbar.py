import streamlit as st

def show_navbar():

    tab = st.radio(
        "",
        ["Stocks", "Options", "Futures"],
        horizontal=True
    )

    return tab
