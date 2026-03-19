import plotly.graph_objects as go
import streamlit as st

def show_oi_chart(df):

    fig = go.Figure()

    fig.add_bar(x=df["Strike"], y=df["Call OI"], name="Call OI")
    fig.add_bar(x=df["Strike"], y=df["Put OI"], name="Put OI")

    fig.update_layout(
        barmode="group",
        height=400,
        template="plotly_dark"
    )

    st.plotly_chart(fig, use_container_width=True)
