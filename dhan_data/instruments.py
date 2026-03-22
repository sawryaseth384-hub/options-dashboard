import pandas as pd
import streamlit as st

URL = "https://images.dhan.co/api-data/api-scrip-master.csv"

@st.cache_data(ttl=3600)
def load_instruments():
    df = pd.read_csv(URL, low_memory=False)

    # --- Auto‑detect exchange column ---
    if "EXCH_ID" not in df.columns:
        exch_col = next((c for c in df.columns if "EXCH" in c.upper()), None)
        if exch_col:
            df = df.rename(columns={exch_col: "EXCH_ID"})
        else:
            raise KeyError(f"No exchange column found. Columns: {df.columns.tolist()}")

    # --- Auto‑detect segment column ---
    if "SEGMENT" not in df.columns:
        seg_col = next((c for c in df.columns if "SEGMENT" in c.upper()), None)
        if seg_col:
            df = df.rename(columns={seg_col: "SEGMENT"})
        else:
            raise KeyError(f"No segment column found. Columns: {df.columns.tolist()}")

    # Keep only NSE
    df = df[df["EXCH_ID"] == "NSE"]
    return df

def get_stock_df():
    df = load_instruments()
    # Stocks are in segment "D"
    stock_df = df[df["SEGMENT"] == "D"]
    # Remove options (contain "-") and futures (contain "FUT")
    stock_df = stock_df[~stock_df["SEM_TRADING_SYMBOL"].str.contains("-", na=False)]
    stock_df = stock_df[~stock_df["SEM_TRADING_SYMBOL"].str.contains("FUT", na=False)]
    stock_df = stock_df[stock_df["SEM_TRADING_SYMBOL"].str.match(r'^[A-Z]+$', na=False)]
    return stock_df[["SEM_TRADING_SYMBOL", "SEM_SMST_SECURITY_ID", "SEGMENT"]].drop_duplicates(subset="SEM_TRADING_SYMBOL")

def get_index_df():
    # Indices are not always in the CSV – fallback to hardcoded IDs if needed
    indices = [
        {"SEM_TRADING_SYMBOL": "NIFTY",    "SEM_SMST_SECURITY_ID": 13, "SEGMENT": "IDX_I"},
        {"SEM_TRADING_SYMBOL": "BANKNIFTY","SEM_SMST_SECURITY_ID": 25, "SEGMENT": "IDX_I"},
        {"SEM_TRADING_SYMBOL": "FINNIFTY", "SEM_SMST_SECURITY_ID": 27, "SEGMENT": "IDX_I"},
    ]
    return pd.DataFrame(indices)

@st.cache_data
def get_instrument_df():
    stock_df = get_stock_df()
    index_df = get_index_df()
    return pd.concat([stock_df, index_df], ignore_index=True)

def get_symbol_data(symbol):
    symbol = symbol.upper()
    df = get_instrument_df()
    match = df[df["SEM_TRADING_SYMBOL"] == symbol]
    if match.empty:
        return None, None
    row = match.iloc[0]
    return int(row["SEM_SMST_SECURITY_ID"]), row["SEGMENT"]
