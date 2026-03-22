# instruments.py
import pandas as pd
import streamlit as st

@st.cache_data
def load_instruments():
    url = "https://images.dhan.co/api-data/api-scrip-master.csv"
    df = pd.read_csv(url)

    # ---- Auto‑detect exchange column ----
    if "EXCH_ID" not in df.columns:
        # Look for column containing "EXCH" or "exchange" (case‑insensitive)
        exch_candidates = [col for col in df.columns if "EXCH" in col.upper() or "EXCHANGE" in col.upper()]
        if exch_candidates:
            exch_col = exch_candidates[0]
            df = df.rename(columns={exch_col: "EXCH_ID"})
        else:
            raise KeyError(f"No exchange column found. Available columns: {df.columns.tolist()}")

    # ---- Auto‑detect segment column ----
    if "SEGMENT" not in df.columns:
        # Look for column containing "SEGMENT" or "EXCHANGE_SEGMENT"
        seg_candidates = [col for col in df.columns if "SEGMENT" in col.upper()]
        if seg_candidates:
            seg_col = seg_candidates[0]
            df = df.rename(columns={seg_col: "SEGMENT"})
        else:
            # If still not found, raise a clear error
            raise KeyError(f"No segment column found. Available columns: {df.columns.tolist()}")

    # Keep only NSE instruments
    df = df[df["EXCH_ID"] == "NSE"]

    # Optional: print unique segment values to help debugging
    print("Unique segment values:", df["SEGMENT"].unique())

    return df

def get_stock_df():
    df = load_instruments()
    # Filter only cash segment (often "D" for derivative base, but we keep only those without "-")
    # We assume "SEGMENT" == "D" for stocks (cash). If values differ, adjust accordingly.
    stock_df = df[df["SEGMENT"] == "D"]
    stock_df = stock_df[~stock_df["SEM_TRADING_SYMBOL"].str.contains("-")]
    stock_df = stock_df[~stock_df["SEM_TRADING_SYMBOL"].str.contains("FUT")]
    stock_df = stock_df[stock_df["SEM_TRADING_SYMBOL"].str.isalpha()]
    return stock_df[["SEM_TRADING_SYMBOL", "SEM_SMST_SECURITY_ID", "SEGMENT"]]

def get_index_df():
    # Manual index list (these are not present in the CSV)
    data = [
        ["NIFTY", 13, "IDX_I"],
        ["BANKNIFTY", 25, "IDX_I"],
        ["FINNIFTY", 27, "IDX_I"]
    ]
    df = pd.DataFrame(data, columns=["SEM_TRADING_SYMBOL", "SEM_SMST_SECURITY_ID", "SEGMENT"])
    return df

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
