import streamlit as st

def show_option_table(df):

    st.subheader("Option Chain")

    st.dataframe(df, use_container_width=True)
