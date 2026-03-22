import pandas as pd
import streamlit as st

@st.cache_data
def load_instruments():
    url = "https://images.dhan.co/api-data/api-scrip-master.csv"
    df = pd.read_csv(url)

    # Detect column names
    if "EXCH_ID" not in df.columns:
        exch_candidates = [col for col in df.columns if "EXCH" in col.upper() or "EXCHANGE" in col.upper()]
        if exch_candidates:
            df = df.rename(columns={exch_candidates[0]: "EXCH_ID"})
    if "SEGMENT" not in df.columns:
        seg_candidates = [col for col in df.columns if "SEGMENT" in col.upper()]
        if seg_candidates:
            df = df.rename(columns={seg_candidates[0]: "SEGMENT"})

    df = df[df["EXCH_ID"] == "NSE"]
    return df

def get_stock_df():
    df = load_instruments()
    # For stocks, segment = "D" and no hyphen
    stock_df = df[df["SEGMENT"] == "D"]
    stock_df = stock_df[~stock_df["SEM_TRADING_SYMBOL"].str.contains("-")]
    stock_df = stock_df[~stock_df["SEM_TRADING_SYMBOL"].str.contains("FUT")]
    stock_df = stock_df[stock_df["SEM_TRADING_SYMBOL"].str.isalpha()]
    return stock_df[["SEM_TRADING_SYMBOL", "SEM_SMST_SECURITY_ID", "SEGMENT"]]

def get_index_df():
    # Now we get indices from the master CSV
    df = load_instruments()
    index_df = df[df["SEGMENT"] == "IDX_I"]
    # Keep only the symbols we care about (optional)
    index_df = index_df[index_df["SEM_TRADING_SYMBOL"].isin(["NIFTY", "BANKNIFTY", "FINNIFTY"])]
    return index_df[["SEM_TRADING_SYMBOL", "SEM_SMST_SECURITY_ID", "SEGMENT"]]

@st.cache_data
def get_instrument_df():
    stock_df = get_stock_df()
    index_df = get_index_df()
    df = pd.concat([stock_df, index_df], ignore_index=True)
    return df

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
