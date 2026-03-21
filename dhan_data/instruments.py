import pandas as pd
import streamlit as st

# =========================
# 📥 LOAD DHAN MASTER CSV
# =========================
@st.cache_data
def load_instruments():
    url = "https://images.dhan.co/api-data/api-scrip-master.csv"

    df = pd.read_csv(url)

    # Only NSE
    df = df[df["EXCH_ID"] == "NSE"]

    return df


# =========================
# 📊 STOCK DATA (CASH / FNO BASE)
# =========================
def get_stock_df():
    df = load_instruments()

    # Derivative base symbols (no CE/PE)
    df = df[df["SEGMENT"] == "D"]

    # Remove options
    df = df[~df["SEM_TRADING_SYMBOL"].str.contains("-")]

    # Remove FUT
    df = df[~df["SEM_TRADING_SYMBOL"].str.contains("FUT")]

    # Keep only clean symbols
    df = df[df["SEM_TRADING_SYMBOL"].str.isalpha()]

    return df[["SEM_TRADING_SYMBOL", "SEM_SMST_SECURITY_ID", "SEGMENT"]]


# =========================
# 📊 INDEX DATA (MANUAL)
# =========================
def get_index_df():

    data = [
        ["NIFTY", 13, "IDX_I"],
        ["BANKNIFTY", 25, "IDX_I"],
        ["FINNIFTY", 27, "IDX_I"]
    ]

    df = pd.DataFrame(data, columns=[
        "SEM_TRADING_SYMBOL",
        "SEM_SMST_SECURITY_ID",
        "SEGMENT"
    ])

    return df


# =========================
# 📦 COMBINED MASTER
# =========================
@st.cache_data
def get_instrument_df():

    stock_df = get_stock_df()
    index_df = get_index_df()

    df = pd.concat([stock_df, index_df], ignore_index=True)

    return df


# =========================
# 🔍 GET SYMBOL DATA
# =========================
def get_symbol_data(symbol):

    symbol = symbol.upper()

    df = get_instrument_df()

    match = df[df["SEM_TRADING_SYMBOL"] == symbol]

    if match.empty:
        return None, None

    row = match.iloc[0]

    security_id = int(row["SEM_SMST_SECURITY_ID"])
    segment = row["SEGMENT"]

    return security_id, segment
