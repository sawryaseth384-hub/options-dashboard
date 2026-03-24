import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import requests
from datetime import datetime, timedelta
from core.token_manager import get_headers

st.set_page_config(layout="wide")
st.title("🧠 Smart Money Options Dashboard — NIFTY (Hardcoded)")

# Hardcoded NIFTY details
SEC_ID = 13
SEGMENT = "IDX_I"

# Generate next Thursday as fallback expiry
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
    st.write("Button clicked! Fetching...")
    url = "https://api.dhan.co/v2/optionchain"
    headers = get_headers()
    headers["Content-Type"] = "application/json"
    payload = {
        "UnderlyingScrip": SEC_ID,
        "UnderlyingSeg": SEGMENT,
        "Expiry": EXPIRY
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        st.write("Response status code:", response.status_code)
        data = response.json()
        st.write("Full API response:")
        st.json(data)  # Show entire response for debugging

        if "errorCode" in data:
            st.error(f"API Error: {data}")
        elif "data" in data:
            raw = data["data"]
            spot = raw.get("last_price", 0)
            oc = raw.get("oc", {})
            if not oc:
                st.warning("No option chain data for this expiry.")
            else:
                rows = []
                for strike, val in oc.items():
                    ce = val.get("ce", {})
                    pe = val.get("pe", {})
                    rows.append({
                        "Strike": int(float(strike)),
                        "CE OI": ce.get("oi", 0),
                        "CE LTP": ce.get("last_price", 0),
                        "CE Delta": ce.get("greeks", {}).get("delta", 0) if ce.get("greeks") else 0,
                        "PE OI": pe.get("oi", 0),
                        "PE LTP": pe.get("last_price", 0),
                        "PE Delta": pe.get("greeks", {}).get("delta", 0) if pe.get("greeks") else 0,
                    })
                df = pd.DataFrame(rows).sort_values("Strike")
                st.write(f"DataFrame shape: {df.shape}")
                st.write("First 5 rows:")
                st.dataframe(df.head(), use_container_width=True)
                if df.empty:
                    st.error("DataFrame is empty!")
                else:
                    st.write(f"Spot price: {spot}")
                    fig = px.bar(df, x="Strike", y=["CE OI", "PE OI"], title="OI by Strike")
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.write("Unexpected response format")
    except Exception as e:
        st.error(f"Exception: {e}")
        import traceback
        st.code(traceback.format_exc())
