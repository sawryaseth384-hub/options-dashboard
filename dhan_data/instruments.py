# instruments.py
import pandas as pd
import streamlit as st

@st.cache_data
def load_instruments():
    url = "https://images.dhan.co/api-data/api-scrip-master.csv"
    df = pd.read_csv(url)

    # 🔍 Debug: log column names (visible in Streamlit logs)
    print("Columns in master CSV:", df.columns.tolist())

    # 🔧 Automatically detect the exchange column
    if "EXCH_ID" not in df.columns:
        # Look for column containing "EXCH" or "exchange" (case-insensitive)
        exch_cols = [col for col in df.columns if "EXCH" in col.upper() or "EXCHANGE" in col.upper()]
        if exch_cols:
            exch_col = exch_cols[0]
            print(f"Using '{exch_col}' as exchange column")
            df = df.rename(columns={exch_col: "EXCH_ID"})
        else:
            # If still not found, raise a clear error
            raise KeyError("No exchange column found in master CSV. Available columns: " + ", ".join(df.columns))

    # Keep only NSE instruments
    df = df[df["EXCH_ID"] == "NSE"]
    return df

def get_stock_df():
    df = load_instruments()
    df = df[df["SEGMENT"] == "D"]
    df = df[~df["SEM_TRADING_SYMBOL"].str.contains("-")]
    df = df[~df["SEM_TRADING_SYMBOL"].str.contains("FUT")]
    df = df[df["SEM_TRADING_SYMBOL"].str.isalpha()]
    return df[["SEM_TRADING_SYMBOL", "SEM_SMST_SECURITY_ID", "SEGMENT"]]

def get_index_df():
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
