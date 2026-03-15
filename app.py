import streamlit as st
import requests
import pandas as pd

st.title("AI Options Trading Dashboard")

headers = {
    "User-Agent": "Mozilla/5.0"
}

session = requests.Session()
session.get("https://www.nseindia.com", headers=headers)

url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"

try:

    response = session.get(url, headers=headers)
    data = response.json()

    records = data["records"]["data"]
    nifty_price = data["records"]["underlyingValue"]

    st.metric("NIFTY Price", nifty_price)

    ce_total = 0
    pe_total = 0

    table = []

    for item in records:

        strike = item["strikePrice"]

        ce = item.get("CE")
        pe = item.get("PE")

        ce_oi = ce["openInterest"] if ce else 0
        pe_oi = pe["openInterest"] if pe else 0

        ce_total += ce_oi
        pe_total += pe_oi

        table.append({
            "Strike": strike,
            "CE OI": ce_oi,
            "PE OI": pe_oi
        })

    df = pd.DataFrame(table)

    pcr = round(pe_total / ce_total, 2)

    st.write("PCR:", pcr)

    st.dataframe(df)

except Exception as e:

    st.error(e)
