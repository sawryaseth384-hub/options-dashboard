import streamlit as st
import pandas as pd

def show_options():

    st.subheader("🔥 Options")

    col1, col2 = st.columns([3, 1])

    with col1:
        df = pd.DataFrame({
            "Strike": [24000, 24100, 24200],
            "CE": [100, 120, 150],
            "PE": [80, 90, 110],
        })

        st.dataframe(df, use_container_width=True)

    with col2:
        st.markdown("### ⚙️ Settings")
        st.selectbox("Expiry", ["Weekly", "Monthly"])
