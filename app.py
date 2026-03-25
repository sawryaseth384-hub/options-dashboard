import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, timedelta

# ✅ Token Manager
from core.token_manager import get_token

# ✅ WebSocket
from dhan_data.live_market_feed import start_feed, get_live_price

# =========================
# CONFIG
# =========================
BASE_URL = "https://api.dhan.co/v2"

st.set_page_config(layout="wide")
st.title("🚀 Dhan Full Dashboard")

# =========================
# START WEBSOCKET
# =========================
if "ws_started" not in st.session_state:
    token = get_token()
    if token:
        start_feed(token, st.secrets["CLIENT_ID"])
        st.session_state.ws_started = True
    else:
        st.error("❌ Token Error")
        st.stop()

# =========================
# HEADERS
# =========================
def get_headers():
    return {
        "access-token": get_token(),
        "client-id": st.secrets["CLIENT_ID"],
        "Content-Type": "application/json"
    }

# =========================
# SAFE POST
# =========================
_last_call = 0

def safe_post(url, payload):
    global _last_call

    wait = max(0, 1 - (time.time() - _last_call))
    if wait > 0:
        time.sleep(wait)

    try:
        res = requests.post(url, headers=get_headers(), json=payload, timeout=10)
        _last_call = time.time()

        if res.status_code != 200:
            return None, f"HTTP {res.status_code}"

        data = res.json()

        if "808" in str(data):
            return None, "Token Expired"

        return data, None

    except Exception as e:
        return None, str(e)

# =========================
# SYMBOLS
# =========================
symbols = {
    "NIFTY": (13, "IDX_I", "INDEX"),
    "RELIANCE": (2885, "NSE_EQ", "EQUITY"),
}

st.subheader("📊 SYMBOLS")
for k, v in symbols.items():
    st.write(k, v)

# =========================
# LIVE LTP
# =========================
st.subheader("📈 LIVE LTP")
ltp = get_live_price()

if ltp > 0:
    st.success(f"🔥 LIVE LTP: {round(ltp, 2)}")
else:
    st.warning("⏳ Waiting for live data...")

# =========================
# MARKET DEPTH
# =========================
def get_depth(sec, seg):
    payload = {seg: [int(sec)]}

    data, err = safe_post(f"{BASE_URL}/marketfeed/ltp", payload)

    if err:
        return None, err

    try:
        d = data["data"][seg][str(sec)]

        return {
            "LTP": d.get("last_price"),
            "High": d.get("high"),
            "Low": d.get("low"),
            "Open": d.get("open"),
        }, None

    except:
        return None, "Depth Parse Error"

st.subheader("📊 MARKET DEPTH")

sec, seg, inst = symbols["RELIANCE"]

depth, d_err = get_depth(sec, seg)

if depth:
    col1, col2, col3 = st.columns(3)
    col1.metric("LTP", depth["LTP"])
    col2.metric("High", depth["High"])
    col3.metric("Low", depth["Low"])
else:
    st.warning(f"Depth Error: {d_err}")

# =========================
# HISTORICAL
# =========================
def get_historical(sec, seg, inst):
    payload = {
        "securityId": str(sec),
        "exchangeSegment": seg,
        "instrument": inst,
        "expiryCode": 0,
        "oi": False,
        "fromDate": (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d"),
        "toDate": datetime.now().strftime("%Y-%m-%d"),
    }

    data, err = safe_post(f"{BASE_URL}/charts/historical", payload)

    if err:
        return None, err

    if not data or "open" not in data:
        return None, "No Data"

    return pd.DataFrame(data), None

st.subheader("📅 HISTORICAL")

hist, _ = get_historical(sec, seg, inst)

if hist is not None:
    st.dataframe(hist.tail())
else:
    st.warning("No historical data")

# =========================
# CANDLE
# =========================
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

    if err:
        return None, err

    return pd.DataFrame(data), None

st.subheader("🕯 CANDLE")

candle, _ = get_intraday(sec, seg, inst)

if candle is not None:
    st.line_chart(candle["close"])
else:
    st.warning("No candle data")

# =========================
# OPTION CHAIN
# =========================
def get_expiry(sec):
    payload = {
        "UnderlyingScrip": sec,
        "UnderlyingSeg": "IDX_I"
    }

    data, err = safe_post(f"{BASE_URL}/optionchain/expirylist", payload)

    if err:
        return [], err

    return data.get("data", []), None


def get_chain(sec, expiry):
    payload = {
        "UnderlyingScrip": sec,
        "UnderlyingSeg": "IDX_I",
        "Expiry": expiry
    }

    data, err = safe_post(f"{BASE_URL}/optionchain", payload)

    if err:
        return None, err

    return data.get("data", {}), None


st.subheader("📊 OPTION CHAIN")

nifty_sec, _, _ = symbols["NIFTY"]

expiries, _ = get_expiry(nifty_sec)

if expiries:
    selected_exp = st.selectbox("Select Expiry", expiries)

    chain, _ = get_chain(nifty_sec, selected_exp)

    if chain:
        st.write(f"Strikes: {len(chain.get('oc', {}))}")
    else:
        st.warning("Chain error")

# =========================
# DEBUG PANEL
# =========================
st.subheader("🛠 DEBUG PANEL")

st.write("Token:", "✅")
st.write("Live LTP:", round(ltp, 2))
st.write("Depth:", "OK" if depth else "FAIL")
st.write("Historical:", "OK" if hist is not None else "FAIL")
st.write("Candle:", "OK" if candle is not None else "FAIL")
st.write("Expiry:", "OK" if expiries else "FAIL")
st.write("Option Chain:", "OK" if 'chain' in locals() and chain else "FAIL")

# =========================
# AUTO REFRESH
# =========================
time.sleep(2)
st.rerun()
