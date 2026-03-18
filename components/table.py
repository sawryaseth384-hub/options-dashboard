import streamlit as st

def render_table(rows):
    st.subheader("📊 Market Data")
    st.dataframe(rows, use_container_width=True)
