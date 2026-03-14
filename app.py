import streamlit as st
import pandas as pd
import numpy as np

st.title("AI Options Dashboard")

data = pd.DataFrame(
    np.random.randn(50, 3),
    columns=["NIFTY", "BANKNIFTY", "FINNIFTY"]
)

st.line_chart(data)
