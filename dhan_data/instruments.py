import pandas as pd
import streamlit as st

URL = "https://images.dhan.co/api-data/api-scrip-master.csv"


# =========================
# 🔥 LOAD DATA
# =========================
@st.cache_data(ttl=3600)
def load_instruments():
    df = pd.read_csv(URL, low_memory=False)

    # ✅ Only NSE
    df = df[df["SEM_EXM_EXCH_ID"] == "NSE"]

    return df


# =========================
# 🔥 STOCK (ONLY UNDERLYING)
# =========================
def get_stock_df():
    df = load_instruments()

    # ✅ Only derivatives segment
    df = df[df["SEM_SEGMENT"] == "D"]

    # ❌ REMOVE OPTIONS (CE/PE)
    df = df[~df["SEM_TRADING_SYMBOL"].str.contains("-", na=False)]

    # ❌ REMOVE FUTURES
    df = df[~df["SEM_TRADING_SYMBOL"].str.contains("FUT", na=False)]

    # ❌ REMOVE TEST
    df = df[~df["SEM_TRADING_SYMBOL"].str.contains("TEST", na=False)]

    # ✅ ONLY PURE STOCK NAMES
    df = df[df["SEM_TRADING_SYMBOL"].str.match(r'^[A-Z]+$', na=False)]

    # ✅ Required columns
    df = df[[
        "SEM_TRADING_SYMBOL",
        "SEM_SMST_SECURITY_ID",
        "SEM_SEGMENT"
    ]]

    return df.drop_duplicates(subset=["SEM_TRADING_SYMBOL"])


# =========================
# 🔥 INDEX (MANUAL FIX)
# =========================
def get_index_df():
    data = [
        {"SEM_TRADING_SYMBOL": "NIFTY", "SEM_SMST_SECURITY_ID": 13, "SEM_SEGMENT": "I"},
        {"SEM_TRADING_SYMBOL": "BANKNIFTY", "SEM_SMST_SECURITY_ID": 25, "SEM_SEGMENT": "I"},
        {"SEM_TRADING_SYMBOL": "FINNIFTY", "SEM_SMST_SECURITY_ID": 27, "SEM_SEGMENT": "I"},
    ]

    return pd.DataFrame(data)


# =========================
# 🔥 MASTER LIST
# =========================
def get_instrument_df():
    df_stock = get_stock_df()
    df_index = get_index_df()

    return pd.concat([df_stock, df_index], ignore_index=True)
