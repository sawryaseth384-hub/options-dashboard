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

    # ✅ Only Equity segment
    df = df[df["SEM_SEGMENT"] == "E"]

    # ✅ Clean symbols (only A-Z)
    df = df[df["SEM_TRADING_SYMBOL"].str.match(r'^[A-Z]+$', na=False)]

    # ❌ Remove TEST
    df = df[~df["SEM_TRADING_SYMBOL"].str.contains("TEST", na=False)]

    return df


# =========================
# 📈 STOCK LIST
# =========================
def get_stock_list():
    df = load_instruments()

    stocks = df["SEM_TRADING_SYMBOL"].dropna().unique().tolist()

    return sorted(stocks)


# =========================
# 📊 INDEX LIST
# =========================
def get_index_list():
    return ["NIFTY", "BANKNIFTY", "FINNIFTY"]


# =========================
# 🔥 MASTER (OPTIONAL)
# =========================
def get_all_instruments():
    """
    Optional combined list (future use)
    """
    stocks = get_stock_list()
    index = get_index_list()

    return {
        "index": index,
        "stocks": stocks
    }
