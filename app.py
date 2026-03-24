import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from dhan_data.option_chain import get_option_chain
from core.token_manager import get_headers

st.set_page_config(layout="wide")
st.title("🧠 Smart Money Options Dashboard — NIFTY (Test)")

# Hardcoded NIFTY details
SEC_ID = 13
SEGMENT = "IDX_I"

# Generate next Thursday as expiry
def get_next_thursday():
    today = datetime.now()
    days_ahead = (3 - today.weekday() + 7) % 7
    if days_ahead == 0:
        days_ahead = 7
    next_thu = today + timedelta(days=days_ahead)
    return next_thu.strftime("%Y-%m-%d")

EXPIRY = get_next_thursday()

st.sidebar.write(f"Using expiry: {EXPIRY}")

if st.button("Load Option Chain"):
    data = get_option_chain(SEC_ID, EXPIRY, SEGMENT)
    if not data or "data" not in data:
        st.error("No data received. Check token and expiry.")
    else:
        raw = data["data"]
        spot = raw.get("last_price", 0)
        oc = raw.get("oc", {})
        rows = []
        for strike, val in oc.items():
            ce = val.get("ce", {})
            pe = val.get("pe", {})
            rows.append({
                "Strike": int(float(strike)),
                "CE OI": ce.get("oi", 0),
                "CE LTP": ce.get("last_price", 0),
                "CE Delta": ce.get("greeks", {}).get("delta", 0),
                "PE OI": pe.get("oi", 0),
                "PE LTP": pe.get("last_price", 0),
                "PE Delta": pe.get("greeks", {}).get("delta", 0),
            })
        df = pd.DataFrame(rows).sort_values("Strike")
        st.success("Data loaded!")
        st.write(f"Spot: {spot}")
        st.dataframe(df, use_container_width=True)
        fig = px.bar(df, x="Strike", y=["CE OI", "PE OI"], barmode="group", title="OI by Strike")
        st.plotly_chart(fig, use_container_width=True)
