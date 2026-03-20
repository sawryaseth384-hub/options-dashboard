import pandas as pd
import streamlit as st

URL = "https://images.dhan.co/api-data/api-scrip-master.csv"


# =========================
# 🔥 LOAD DATA
# =========================
@st.cache_data(ttl=3600)
def load_instruments():
    df = pd.read_csv(URL)

    # ✅ Only NSE
    df = df[df["SEM_EXM_EXCH_ID"] == "NSE"]

    # ❌ Remove TEST symbols
    df = df[~df["SEM_TRADING_SYMBOL"].str.contains("TEST", na=False)]

    # ❌ Remove futures/options → only EQUITY
    df = df[df["SEM_INSTRUMENT_NAME"] == "EQUITY"]

    return df


# =========================
# 🔥 GET CLEAN LIST
# =========================
def get_instrument_list():
    df = load_instruments()

    symbols = df["SEM_TRADING_SYMBOL"].dropna().unique().tolist()

    # ✅ Add Index manually
    extra = ["NIFTY", "BANKNIFTY", "FINNIFTY"]

    final_list = sorted(list(set(symbols + extra)))

    return final_list
