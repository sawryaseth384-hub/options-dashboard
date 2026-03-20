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

    # ❌ Remove TEST
    df = df[~df["SEM_TRADING_SYMBOL"].str.contains("TEST", na=False)]

    # Drop null
    df = df.dropna(subset=["SEM_TRADING_SYMBOL", "SEM_SMST_SECURITY_ID"])

    return df


# =========================
# 📈 STOCK DF (IMPORTANT)
# =========================
def get_stock_df():
    df = load_instruments()

    # Equity only
    df = df[df["SEM_SEGMENT"] == "E"]

    df = df[[
        "SEM_TRADING_SYMBOL",
        "SEM_SMST_SECURITY_ID",
        "SEM_SEGMENT"
    ]]

    return df


# =========================
# 📊 INDEX DF (MANUAL)
# =========================
def get_index_df():
    data = [
        {"SEM_TRADING_SYMBOL": "NIFTY", "SEM_SMST_SECURITY_ID": 13, "SEM_SEGMENT": "I"},
        {"SEM_TRADING_SYMBOL": "BANKNIFTY", "SEM_SMST_SECURITY_ID": 25, "SEM_SEGMENT": "I"},
        {"SEM_TRADING_SYMBOL": "FINNIFTY", "SEM_SMST_SECURITY_ID": 27, "SEM_SEGMENT": "I"},
    ]

    return pd.DataFrame(data)


# =========================
# 🔥 MASTER DF (MOST IMPORTANT)
# =========================
def get_instrument_df():
    stock_df = get_stock_df()
    index_df = get_index_df()

    df = pd.concat([stock_df, index_df], ignore_index=True)

    return df


# =========================
# 📋 LIST (UI USE)
# =========================
def get_symbol_list():
    df = get_instrument_df()
    return sorted(df["SEM_TRADING_SYMBOL"].unique().tolist())
