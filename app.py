import streamlit as st
import pandas as pd
import os
from dhanhq import dhanhq

st.set_page_config(layout="wide", page_title="Options Dashboard")

# ---------- DHAN CONNECTION ----------

def get_dhan():

    client_id = os.environ.get("DHAN_CLIENT_ID")
    access_token = os.environ.get("DHAN_ACCESS_TOKEN")

    if not client_id or not access_token:
        return None

    try:
        dhan = dhanhq(client_id, access_token)
        return dhan
    except:
        return None


# ---------- FETCH NIFTY PRICE ----------

def get_nifty_price():

    dhan = get_dhan()

    if dhan is None:
        return None

    try:

        data = dhan.marketfeed(
            exchange_segment="NSE_EQ",
            security_id="13"
        )

        return data["last_price"]

    except:
        return None


# ---------- SAMPLE OPTION DATA ----------

def sample_option_data():

    strikes = [22000,22100,22200,22300,22400]

    df = pd.DataFrame({
        "Strike": strikes,
        "Call_OI": [52000,61000,72000,48000,35000],
        "Put_OI": [30000,45000,80000,92000,61000]
    })

    return df


# ---------- METRICS ----------

def calculate_metrics(df):

    call_oi = df["Call_OI"].sum()
    put_oi = df["Put_OI"].sum()

    pcr = put_oi / call_oi if call_oi != 0 else 0

    resistance = df.loc[df["Call_OI"].idxmax(),"Strike"]
    support = df.loc[df["Put_OI"].idxmax(),"Strike"]

    return pcr,support,resistance


# ---------- DASHBOARD ----------

st.title("Options Trading Dashboard (Dhan Data)")

nifty_price = get_nifty_price()

df = sample_option_data()

pcr,support,resistance = calculate_metrics(df)

col1,col2,col3,col4 = st.columns(4)

col1.metric("NIFTY LTP",nifty_price)
col2.metric("PCR",round(pcr,2))
col3.metric("Support",support)
col4.metric("Resistance",resistance)

st.subheader("Option Data")

st.dataframe(df)
