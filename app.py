import streamlit as st
from ai_engine.signal_generator import generate_signal

st.title("AI Options War Room")

pcr = 1.15

signal = generate_signal(pcr)

st.metric("PCR", pcr)

st.subheader("AI Signal")

if signal == "BULLISH":
    st.success("BUY CALL")

elif signal == "BEARISH":
    st.error("BUY PUT")

else:
    st.warning("NO TRADE")
