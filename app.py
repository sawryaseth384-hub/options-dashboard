import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="AI Options Dashboard", layout="wide")

st.title("AI Options Trading Dashboard")

# NSE headers
headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json"
}

# NSE session
session = requests.Session()
session.get("https://www.nseindia.com", headers=headers)

url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"

try:

    response = session.get(url, headers=headers)
    data = response.json()

    records = data["records"]["data"]
    underlying = data["records"]["underlyingValue"]

    st.metric("NIFTY Price", underlying)

    ce_oi = 0
    pe_oi = 0

    table_data = []

    for i in records:

        strike = i["strikePrice"]

        ce = i.get("CE")
        pe = i.get("PE")

        ce_oi_val = ce["openInterest"] if ce else 0
        pe_oi_val = pe["openInterest"] if pe else 0

        ce_ltp = ce["lastPrice"] if ce else 0
        pe_ltp = pe["lastPrice"] if pe else 0

        ce_oi += ce_oi_val
        pe_oi += pe_oi_val

        table_data.append({
            "Strike": strike,
            "CE OI": ce_oi_val,
            "CE LTP": ce_ltp,
            "PE LTP": pe_ltp,
            "PE OI": pe_oi_val
        })

    df = pd.DataFrame(table_data)

    pcr = round(pe_oi / ce_oi, 2)

    col1, col2, col3 = st.columns(3)

    col1.metric("Total CE OI", ce_oi)
    col2.metric("Total PE OI", pe_oi)
    col3.metric("PCR", pcr)

    st.subheader("Option Chain")

    st.dataframe(df, use_container_width=True)

except Exception as e:

    st.error(e)
