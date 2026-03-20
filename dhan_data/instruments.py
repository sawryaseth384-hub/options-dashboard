import pandas as pd
import streamlit as st

URL = "https://images.dhan.co/api-data/api-scrip-master.csv"

@st.cache_data(ttl=3600)
def load_instruments():
    df = pd.read_csv(URL)

    # 🔥 Only NSE + Equity/Derivatives
    df = df[df["SEM_EXM_EXCH_ID"] == "NSE"]

    return df


def get_instrument_list():
    df = load_instruments()

    # 🔥 Unique symbols
    symbols = df["SEM_TRADING_SYMBOL"].dropna().unique().tolist()

    return sorted(symbols)
