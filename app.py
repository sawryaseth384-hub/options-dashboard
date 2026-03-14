import streamlit as st
import pandas as pd
import requests

st.title("AI Options Dashboard")

url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"

headers = {
    "User-Agent": "Mozilla/5.0"
}

try:
    r = requests.get(url, headers=headers)
    data = r.json()

    records = data['records']['data']

    rows = []

    for i in records:
        strike = i['strikePrice']

        call_oi = None
        put_oi = None

        if "CE" in i:
            call_oi = i["CE"]["openInterest"]

        if "PE" in i:
            put_oi = i["PE"]["openInterest"]

        rows.append({
            "Strike Price": strike,
            "Call OI": call_oi,
            "Put OI": put_oi
        })

    df = pd.DataFrame(rows)

    st.subheader("NIFTY Option Chain")
    st.dataframe(df)

except:
    st.error("Failed to fetch NSE data")
