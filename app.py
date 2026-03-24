import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, timedelta
from core.token_manager import get_headers
from dhan_data.expiry import get_expiry

st.set_page_config(layout="wide")
st.title("🧠 Smart Money Options Dashboard — NIFTY (Hardcoded)")

SEC_ID = 13
SEGMENT = "IDX_I"

# Fetch expiry list
st.write("Fetching expiry list...")
expiry_data = get_expiry(SEC_ID)
st.write("Expiry API response:", expiry_data)

if expiry_data:
    # Extract list from response (handle different structures)
    if isinstance(expiry_data, list):
        expiry_list = expiry_data
    elif isinstance(expiry_data, dict) and "data" in expiry_data:
        expiry_list = expiry_data["data"]
    else:
        expiry_list = []
    
    if expiry_list:
        st.write("Available expiries:", expiry_list)
        selected_expiry = st.selectbox("Select Expiry", expiry_list)
        st.write(f"Selected expiry: {selected_expiry}")
        
        if st.button("Load Option Chain"):
            url = "https://api.dhan.co/v2/optionchain"
            headers = get_headers()
            headers["Content-Type"] = "application/json"
            payload = {
                "UnderlyingScrip": SEC_ID,
                "UnderlyingSeg": SEGMENT,
                "Expiry": selected_expiry
            }
            with st.spinner("Fetching..."):
                try:
                    response = requests.post(url, headers=headers, json=payload, timeout=10)
                    data = response.json()
                    if "errorCode" in data:
                        st.error(f"API Error: {data}")
                    elif "data" in data:
                        raw = data["data"]
                        spot = raw.get("last_price", 0)
                        oc = raw.get("oc", {})
                        if oc:
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
                            st.write(f"Spot: {spot}")
                            st.dataframe(df, use_container_width=True)
                            fig = px.bar(df, x="Strike", y=["CE OI", "PE OI"], title="OI by Strike")
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.warning("No option chain data for this expiry.")
                    else:
                        st.json(data)
                except Exception as e:
                    st.error(f"Error: {e}")
    else:
        st.error("No expiry list found.")
else:
    st.error("Failed to fetch expiry list.")
