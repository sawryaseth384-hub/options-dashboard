import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh

from core.token_manager import get_token
from dhan_data.live_market_feed import start_feed, get_live_price

# =========================
# CONFIG
# =========================
BASE_URL = "https://api.dhan.co/v2"

st.set_page_config(layout="wide")
st.title("🚀 PRO TRADING DASHBOARD")

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
# WS START
# =========================
if not st.session_state.get("ws_started", False):
    try:
        start_feed(token, CLIENT_ID)
        st.session_state["ws_started"] = True
    except Exception as e:
        st.error(f"WS Error: {e}")

# =========================
# HEADERS
# =========================
def get_headers():
    return {
        "access-token": get_token(),
        "client-id": CLIENT_ID,
        "Content-Type": "application/json"
    }

# =========================
# SAFE POST
# =========================
_last_call = 0

def safe_post(url, payload):
    global _last_call

    wait = max(0, 1.2 - (time.time() - _last_call))
    if wait > 0:
        time.sleep(wait)

    for _ in range(3):
        try:
            res = requests.post(url, headers=get_headers(), json=payload, timeout=10)

            if res.status_code == 200:
                data = res.json()
                if data:
                    return data, None

            time.sleep(1)

        except:
            time.sleep(1)

    return None, "API Failed"

# =========================
# SYMBOLS
# =========================
symbols = {
    "NIFTY": (13, "IDX_I", "INDEX"),
    "RELIANCE": (2885, "NSE_EQ", "EQUITY"),
}

symbol_name = st.selectbox("Select Symbol", list(symbols.keys()))
sec, seg, inst = symbols[symbol_name]

# =========================
# LIVE LTP
# =========================
st.subheader("📈 LIVE LTP")

ltp = get_live_price()
try:
    ltp = float(ltp)
except:
    ltp = 0

if ltp > 0:
    st.success(f"{symbol_name} → {round(ltp,2)}")
else:
    st.warning("Waiting for live data...")

# =========================
# DEPTH
# =========================
@st.cache_data(ttl=5)
def get_depth(sec, seg):
    payload = {seg: [int(sec)]}
    data, err = safe_post(f"{BASE_URL}/marketfeed/ltp", payload)

    if err:
        return None

    try:
        d = data["data"][seg][str(sec)]
        return {
            "LTP": float(d.get("last_price", 0)),
            "High": float(d.get("high") or d.get("last_price", 0)),
            "Low": float(d.get("low") or d.get("last_price", 0)),
        }
    except:
        return None

st.subheader("📊 MARKET DEPTH")

depth = get_depth(sec, seg)

if depth:
    c1, c2, c3 = st.columns(3)
    c1.metric("LTP", depth["LTP"])
    c2.metric("High", depth["High"])
    c3.metric("Low", depth["Low"])

# =========================
# INTRADAY
# =========================
@st.cache_data(ttl=10)
def get_intraday(sec, seg, inst):
    payload = {
        "securityId": str(sec),
        "exchangeSegment": seg,
        "instrument": inst,
        "interval": "1",
        "oi": False,
        "fromDate": datetime.now().strftime("%Y-%m-%d"),
        "toDate": datetime.now().strftime("%Y-%m-%d"),
    }

    data, err = safe_post(f"{BASE_URL}/charts/intraday", payload)

    if err or not data:
        return None

    df = pd.DataFrame(data)

    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df = df.dropna(subset=["close"])

    if "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"])
        df = df.set_index("datetime")

    return df

st.subheader("🕯 INTRADAY")

candle = get_intraday(sec, seg, inst)

if candle is not None and not candle.empty:
    st.line_chart(candle["close"])
else:
    st.warning("No Data")

# =========================
# OPTION CHAIN + PCR
# =========================
@st.cache_data(ttl=300)
def get_expiry(sec):
    payload = {"UnderlyingScrip": int(sec), "UnderlyingSeg": "IDX_I"}
    data, err = safe_post(f"{BASE_URL}/optionchain/expirylist", payload)

    if err or not data:
        return []

    return data.get("data", [])

@st.cache_data(ttl=120)
def get_chain(sec, expiry):
    payload = {
        "UnderlyingScrip": int(sec),
        "UnderlyingSeg": "IDX_I",
        "Expiry": expiry
    }

    data, err = safe_post(f"{BASE_URL}/optionchain", payload)

    if err or not data:
        return None

    return data["data"]["oc"]

st.subheader("📊 OPTION CHAIN + PCR")

expiries = get_expiry(sec)

if expiries:
    expiry = st.selectbox("Expiry", expiries)
    chain = get_chain(sec, expiry)

    if chain:
        df = pd.DataFrame.from_dict(chain, orient="index")

        # ATM FILTER
        df["strike"] = df.index.astype(float)
        atm = df["strike"].median()

        df = df[(df["strike"] > atm - 500) & (df["strike"] < atm + 500)]

        # PCR
        total_put = df["putOi"].sum()
        total_call = df["callOi"].sum()
        pcr = round(total_put / total_call, 2) if total_call else 0

        st.metric("PCR", pcr)

        st.dataframe(df.head(30))

# =========================
# DEBUG
# =========================
st.subheader("🛠 SYSTEM STATUS")

st.write({
    "Token": "OK",
    "WS": st.session_state.get("ws_started", False),
    "LTP": ltp,
    "Depth": depth is not None,
    "Intraday": candle is not None
})
