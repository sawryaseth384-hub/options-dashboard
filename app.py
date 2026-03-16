import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests

st.set_page_config(layout="wide")

st.title("📊 NIFTY AI Options Dashboard")

API_URL = "PUT_COLAB_API_URL_HERE"

data = requests.get(API_URL).json()

spot = data["spot"]
df = pd.DataFrame(data["option_chain"])

st.metric("NIFTY Spot", spot)

st.dataframe(df)

fig = go.Figure()

fig.add_bar(x=df["strike"], y=df["CE_OI"], name="Call OI")
fig.add_bar(x=df["strike"], y=df["PE_OI"], name="Put OI")

st.plotly_chart(fig, use_container_width=True)
