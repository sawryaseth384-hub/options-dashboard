import streamlit as st
import pandas as pd

def show_futures():

    st.subheader("📈 Futures")

    df = pd.DataFrame({
        "Price": [100, 105, 110, 108, 115]
    })

    st.line_chart(df)
