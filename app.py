import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

from core.token_manager import get_token
from dhan_data.live_market_feed import start_feed, get_live_price

# =========================
# CONFIG
# =========================
BASE_URL = "https://api.dhan.co/v2"

st.set_page_config(layout="wide")
st.title("🚀 FIRST TRADING TERMINAL")

st_autorefresh(interval=2000, key="refresh")

CLIENT_ID = st.secrets.get("CLIENT_ID")

if not CLIENT_ID:
    st.error("CLIENT_ID missing")
    st.stop()

token = get_token()
if not token:
    st.error("Token Error")
    st.stop()

# =========================
# SYMBOLS
# =========================
symbols = {
    "NIFTY": (13, "IDX_I", "INDEX"),
    "BANKNIFTY": (25, "IDX_I", "INDEX"),
}

symbol = st.selectbox("Select Market", list(symbols.keys()))
sec, seg, inst = symbols[symbol]

# =========================
# WS START
# =========================
if not st.session_state.get("ws_started", False):
    start_feed(token, CLIENT_ID)
    st.session_state["ws_started"] = True

# =========================
# SAFE API
# =========================
def safe_post(url, payload):
    try:
        res = requests.post(url, headers={
            "access-token": get_token(),
            "client-id": CLIENT_ID,
            "Content-Type": "application/json"
        }, json=payload, timeout=10)

        if res.status_code == 200:
            return res.json()
    except:
        return None

# =========================
# LTP
# =========================
ltp = get_live_price()

try:
    ltp = float(ltp)
except:
    ltp = 0

# =========================
# INTRADAY + EMA
# =========================
def get_intraday():
    payload = {
        "securityId": str(sec),
        "exchangeSegment": seg,
        "instrument": inst,
        "interval": "1",
        "oi": False,
        "fromDate": datetime.now().strftime("%Y-%m-%d"),
        "toDate": datetime.now().strftime("%Y-%m-%d"),
    }

    data = safe_post(f"{BASE_URL}/charts/intraday", payload)

    if not data:
        return None

    df = pd.DataFrame(data)

    if "close" not in df.columns:
        return None

    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df = df.dropna()

    df["EMA"] = df["close"].ewm(span=21).mean()

    return df

df = get_intraday()

# =========================
# TREND
# =========================
trend = "WAIT"

if df is not None and not df.empty:
    last_price = df["close"].iloc[-1]
    ema = df["EMA"].iloc[-1]

    if last_price > ema:
        trend = "BULLISH"
    else:
        trend = "BEARISH"

# =========================
# OPTION CHAIN + PCR
# =========================
def get_chain():
    payload = {
        "UnderlyingScrip": int(sec),
        "UnderlyingSeg": seg,
        "Expiry": "2026-03-30"
    }

    data = safe_post(f"{BASE_URL}/optionchain", payload)

    if not data:
        return None

    return data["data"]["oc"]

chain = get_chain()

total_put = 0
total_call = 0

if chain:
    for strike, row in chain.items():
        try:
            if "CE" in row and "PE" in row:
                total_call += row["CE"].get("oi", 0)
                total_put += row["PE"].get("oi", 0)
        except:
            continue

pcr = round(total_put / total_call, 2) if total_call else 0

# =========================
# FINAL SIGNAL
# =========================
signal = "WAIT"

if trend == "BULLISH" and pcr > 1:
    signal = "BUY CALL"

elif trend == "BEARISH" and pcr < 1:
    signal = "BUY PUT"

# =========================
# UI
# =========================
col1, col2, col3 = st.columns(3)

col1.metric("LTP", round(ltp, 2))
col2.metric("Trend", trend)
col3.metric("PCR", pcr)

st.subheader("🎯 SIGNAL")

if signal == "BUY CALL":
    st.success("🚀 BUY CALL")
elif signal == "BUY PUT":
    st.error("🔻 BUY PUT")
else:
    st.warning("WAIT")

# =========================
# CHART
# =========================
if df is not None:
    st.line_chart(df[["close", "EMA"]])
