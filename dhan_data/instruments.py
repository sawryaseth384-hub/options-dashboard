import pandas as pd
import streamlit as st

URL = "https://images.dhan.co/api-data/api-scrip-master.csv"


@st.cache_data(ttl=3600)
def load_instruments():
    df = pd.read_csv(URL, low_memory=False)

    # ✅ Only NSE
    df = df[df["SEM_EXM_EXCH_ID"] == "NSE"]

    return df


# =========================
# 🔥 STOCK (UNDERLYING ONLY)
# =========================
def get_stock_df():
    df = load_instruments()

    # Only derivatives
    df = df[df["SEM_SEGMENT"] == "D"]

    # ❌ remove FUT / TEST
    df = df[~df["SEM_TRADING_SYMBOL"].str.contains("FUT", na=False)]
    df = df[~df["SEM_TRADING_SYMBOL"].str.contains("TEST", na=False)]

    df = df[[
        "SEM_TRADING_SYMBOL",
        "SEM_SMST_SECURITY_ID",
        "SEM_SEGMENT"
    ]]

    return df.dropna()


# =========================
# 🔥 INDEX
# =========================
def get_index_df():
    data = [
        {"SEM_TRADING_SYMBOL": "NIFTY", "SEM_SMST_SECURITY_ID": 13, "SEM_SEGMENT": "I"},
        {"SEM_TRADING_SYMBOL": "BANKNIFTY", "SEM_SMST_SECURITY_ID": 25, "SEM_SEGMENT": "I"},
        {"SEM_TRADING_SYMBOL": "FINNIFTY", "SEM_SMST_SECURITY_ID": 27, "SEM_SEGMENT": "I"},
    ]

    return pd.DataFrame(data)


# =========================
# 🔥 MASTER
# =========================
def get_instrument_df():
    return pd.concat(
        [get_stock_df(), get_index_df()],
        ignore_index=True
    )
