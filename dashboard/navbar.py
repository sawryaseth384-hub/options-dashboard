# dashboard/navbar.py

import streamlit as st

def show_navbar():

    tab = st.radio(
        "",
        ["Stocks", "AI Options", "Futures"],
        horizontal=True
    )

    return tab
