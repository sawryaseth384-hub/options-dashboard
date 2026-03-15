import streamlit as st
import requests
import pandas as pd

st.title("AI Options Trading Dashboard")

session = requests.Session()

headers = {
    "user-agent": "Mozilla/5.0",
    "accept-language": "en-US,en;q=0.9",
    "accept-encoding": "gzip, deflate, br"
}

# NSE homepage visit (cookie generate)
session.get("https://www.nseindia.com", headers=headers)

url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"

try:

    response = session.get(url, headers=headers)
    data = response.json()

    records = data['records']['data']
    price = data['records']['underlyingValue']

    st.metric("NIFTY PRICE", price)

    table = []

    ce_total = 0
    pe_total = 0

    for i in records:

        strike = i['strikePrice']

        ce = i.get('CE')
        pe = i.get('PE')

        ce_oi = ce['openInterest'] if ce else 0
        pe_oi = pe['openInterest'] if pe else 0

        ce_total += ce_oi
        pe_total += pe_oi

        table.append({
            "Strike": strike,
            "CE OI": ce_oi,
            "PE OI": pe_oi
        })

    df = pd.DataFrame(table)

    pcr = round(pe_total / ce_total, 2)

    st.subheader("PCR")
    st.write(pcr)

    st.subheader("Option Chain")
    st.dataframe(df)

except Exception as e:

    st.error(e)
