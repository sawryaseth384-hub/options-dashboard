import streamlit as st

def show_metrics(df):

    total_call = df["Call OI"].sum()
    total_put = df["Put OI"].sum()

    pcr = round(total_put / total_call, 2)

    max_pain = df.loc[(df["Call OI"] + df["Put OI"]).idxmax(), "Strike"]

    col1, col2, col3 = st.columns(3)

    col1.metric("PCR", pcr)
    col2.metric("Max Pain", max_pain)
    col3.metric("Total OI", f"{(total_call+total_put)/1e7:.2f} Cr")
