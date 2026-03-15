import streamlit as st
import requests
import pandas as pd
import time

st.title("AI Options Trading Dashboard")

headers = {
    "User-Agent": "Mozilla/5.0"
}

session = requests.Session()

try:
    # NSE homepage visit for cookie
    session.get("https://www.nseindia.com", headers=headers, timeout=10)
    time.sleep(1)

    url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
    response = session.get(url, headers=headers, timeout=10)

    data = response.json()

    if "records" not in data:
        st.error("NSE API blocked request. Refresh the page.")
        st.json(data)
        st.stop()

    records = data["records"]["data"]
    price = data["records"]["underlyingValue"]

    st.metric("NIFTY Price", price)

    ce_total = 0
    pe_total = 0
    rows = []

    for item in records:

        strike = item["strikePrice"]

        ce = item.get("CE")
        pe = item.get("PE")

        ce_oi = ce["openInterest"] if ce else 0
        pe_oi = pe["openInterest"] if pe else 0

        ce_total += ce_oi
        pe_total += pe_oi

        rows.append({
            "Strike": strike,
            "CE OI": ce_oi,
            "PE OI": pe_oi
        })

    df = pd.DataFrame(rows)

    pcr = round(pe_total / ce_total, 2)

    st.subheader("Put Call Ratio")
    st.write(pcr)

    st.subheader("Option Chain")
    st.dataframe(df)

except Exception as e:

    st.error("Error loading NSE data")
    st.write(e)
