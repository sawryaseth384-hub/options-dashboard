import pandas as pd
import streamlit as st

URL = "https://images.dhan.co/api-data/api-scrip-master.csv"

@st.cache_data(ttl=3600)
def load_instruments():
    df = pd.read_csv(URL, low_memory=False)

    # Auto‑detect exchange column
    exch_col = next((c for c in df.columns if "EXCH" in c.upper()), None)
    if exch_col:
        df = df.rename(columns={exch_col: "EXCH_ID"})
    else:
        st.error("No exchange column found in master CSV")
        return pd.DataFrame()

    # Auto‑detect segment column
    seg_col = next((c for c in df.columns if "SEGMENT" in c.upper()), None)
    if seg_col:
        df = df.rename(columns={seg_col: "SEGMENT"})
    else:
        st.error("No segment column found in master CSV")
        return pd.DataFrame()

    # Keep only NSE
    df = df[df["EXCH_ID"] == "NSE"]
    return df

def get_stock_df():
    df = load_instruments()
    if df.empty:
        return pd.DataFrame(columns=["SEM_TRADING_SYMBOL", "SEM_SMST_SECURITY_ID", "SEGMENT"])

    # Stocks are in segment "D"
    stock_df = df[df["SEGMENT"] == "D"]
    # Remove options (contain "-") and futures (contain "FUT")
    stock_df = stock_df[~stock_df["SEM_TRADING_SYMBOL"].str.contains("-", na=False)]
    stock_df = stock_df[~stock_df["SEM_TRADING_SYMBOL"].str.contains("FUT", na=False)]
    # Keep only pure alphabetic symbols
    stock_df = stock_df[stock_df["SEM_TRADING_SYMBOL"].str.match(r'^[A-Z]+$', na=False)]

    return stock_df[["SEM_TRADING_SYMBOL", "SEM_SMST_SECURITY_ID", "SEGMENT"]].drop_duplicates(subset="SEM_TRADING_SYMBOL")

def get_index_df():
    df = load_instruments()
    if df.empty:
        # Fallback when CSV is empty
        data = [
            {"SEM_TRADING_SYMBOL": "NIFTY",    "SEM_SMST_SECURITY_ID": 13, "SEGMENT": "IDX_I"},
            {"SEM_TRADING_SYMBOL": "BANKNIFTY","SEM_SMST_SECURITY_ID": 25, "SEGMENT": "IDX_I"},
            {"SEM_TRADING_SYMBOL": "FINNIFTY", "SEM_SMST_SECURITY_ID": 27, "SEGMENT": "IDX_I"},
        ]
        return pd.DataFrame(data)

    # Indices can have SEGMENT = "I" or "IDX_I"
    index_df = df[df["SEGMENT"].isin(["I", "IDX_I"])]
    # Filter to only the major indices
    major_indices = ["NIFTY", "BANKNIFTY", "FINNIFTY"]
    index_df = index_df[index_df["SEM_TRADING_SYMBOL"].isin(major_indices)]

    # If still empty, fallback to hardcoded
    if index_df.empty:
        st.warning("Indices not found in CSV. Using fallback IDs.")
        data = [
            {"SEM_TRADING_SYMBOL": "NIFTY",    "SEM_SMST_SECURITY_ID": 13, "SEGMENT": "IDX_I"},
            {"SEM_TRADING_SYMBOL": "BANKNIFTY","SEM_SMST_SECURITY_ID": 25, "SEGMENT": "IDX_I"},
            {"SEM_TRADING_SYMBOL": "FINNIFTY", "SEM_SMST_SECURITY_ID": 27, "SEGMENT": "IDX_I"},
        ]
        return pd.DataFrame(data)

    # Map segment to "IDX_I" for consistency
    index_df["SEGMENT"] = "IDX_I"
    return index_df[["SEM_TRADING_SYMBOL", "SEM_SMST_SECURITY_ID", "SEGMENT"]]

@st.cache_data
def get_instrument_df():
    stock_df = get_stock_df()
    index_df = get_index_df()
    combined = pd.concat([stock_df, index_df], ignore_index=True)

    # Debug: show NIFTY's security ID
    nifty_row = combined[combined["SEM_TRADING_SYMBOL"] == "NIFTY"]
    if not nifty_row.empty:
        st.write("🔍 NIFTY security ID:", nifty_row.iloc[0]["SEM_SMST_SECURITY_ID"])
    else:
        st.warning("NIFTY not found in combined instrument list")
    return combined

def get_symbol_data(symbol):
    symbol = symbol.upper()
    df = get_instrument_df()
    match = df[df["SEM_TRADING_SYMBOL"] == symbol]
    if match.empty:
        return None, None
    row = match.iloc[0]
    return int(row["SEM_SMST_SECURITY_ID"]), row["SEGMENT"]
