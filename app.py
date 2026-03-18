import streamlit as st
import requests

st.title("📊 DHAN DATA DASHBOARD")

CLIENT_ID = st.secrets["CLIENT_ID"]
ACCESS_TOKEN = st.secrets["ACCESS_TOKEN"]

# 🔥 API CALL BUTTON
if st.button("Fetch Data"):

    url = "https://api.dhan.co/v2/marketfeed/quote"

    headers = {
        "access-token": ACCESS_TOKEN,
        "client-id": CLIENT_ID,
        "Content-Type": "application/json"
    }

    payload = {
        "NSE_EQ": [11536],     # Reliance
        "NSE_FNO": [49081]     # Option
    }

    res = requests.post(url, headers=headers, json=payload)
    data = res.json()

    st.subheader("📡 RAW DATA")
    st.json(data)

    # 🔥 Table View
    if data.get("status") == "success":

        output = []

        for segment, items in data["data"].items():
            for sec_id, values in items.items():

                output.append({
                    "Segment": segment,
                    "SecurityID": sec_id,
                    "Price": values.get("last_price"),
                    "OI": values.get("oi"),
                    "Volume": values.get("volume")
                })

        st.subheader("📊 TABLE VIEW")
        st.dataframe(output)
