import pandas as pd
import streamlit as st

URL = "https://images.dhan.co/api-data/api-scrip-master.csv"


@st.cache_data(ttl=3600)
def load_instruments():
    df = pd.read_csv(URL)

    # ✅ Only NSE
    df = df[df["SEM_EXM_EXCH_ID"] == "NSE"]

    # ✅ Only Equity segment
    df = df[df["SEM_SEGMENT"] == "E"]

    # ✅ Only real stock symbols (no numbers start)
    df = df[df["SEM_TRADING_SYMBOL"].str.match(r'^[A-Z]+$', na=False)]

    # ❌ Remove TEST
    df = df[~df["SEM_TRADING_SYMBOL"].str.contains("TEST", na=False)]

    return df


def get_instrument_list():
    df = load_instruments()

    symbols = df["SEM_TRADING_SYMBOL"].dropna().unique().tolist()

    # ✅ Add index manually
    extra = ["NIFTY", "BANKNIFTY", "FINNIFTY"]

    final = list(set(symbols + extra))

    return sorted(final)
