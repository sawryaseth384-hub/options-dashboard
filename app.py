import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh

# =========================
# CUSTOM MODULES
# =========================
from core.token_manager import get_token
from dhan_data.live_market_feed import start_feed, get_live_price

# =========================
# CONFIG
# =========================
BASE_URL = "https://api.dhan.co/v2"

st.set_page_config(layout="wide")
st.title("🚀 Dhan Smart Dashboard")

# =========================
# AUTO REFRESH (Stable)
# =========================
st_autorefresh(interval=2000, key="refresh")

# =========================
# CLIENT ID SAFE LOAD
# =========================
CLIENT_ID = st.secrets.get("CLIENT_ID")

if not CLIENT_ID:
    st.error("❌ CLIENT_ID missing in secrets")
    st.stop()

# =========================
# TOKEN INIT
# =========================
token = get_token()

if not token:
    st.error("❌ Token Error")
    st.stop()

# =========================
# WEBSOCKET START (SAFE)
# =========================
if not st.session_state.get("ws_started", False):
    start_feed(token, CLIENT_ID)
    st.session_state["ws_started"] = True

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
# SAFE POST (WITH RETRY)
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
            _last_call = time.time()

            if res.status_code == 200:
                data = res.json()

                if data.get("status") == "failure":
                    return None, data.get("remarks", "API Error")

                return data, None

        except Exception as e:
            return None, str(e)

        time.sleep(1)

    return None, "Retry Failed"

# =========================
# SYMBOLS
# =========================
symbols = {
    "NIFTY": (13, "IDX_I", "INDEX"),
    "RELIANCE": (2885, "NSE_EQ", "EQUITY"),
}

st.subheader("📊 SYMBOLS")
st.write(symbols)

# =========================
# LIVE LTP
# =========================
st.subheader("📈 LIVE LTP")

ltp = get_live_price()

if ltp > 0:
    st.success(f"🔥 {round(ltp, 2)}")
else:
    st.warning("⏳ Waiting for live data...")

# =========================
# MARKET DEPTH (CACHED)
# =========================
@st.cache_data(ttl=5)
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
        return None, "Parse Error"

st.subheader("📊 MARKET DEPTH")

sec, seg, inst = symbols["RELIANCE"]
depth, d_err = get_depth(sec, seg)

if depth:
    c1, c2, c3 = st.columns(3)
    c1.metric("LTP", depth["LTP"])
    c2.metric("High", depth["High"])
    c3.metric("Low", depth["Low"])
else:
    st.warning(f"❌ {d_err}")

# =========================
# HISTORICAL DATA
# =========================
@st.cache_data(ttl=60)
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

    if err or not data or "open" not in data:
        return None

    return pd.DataFrame(data)

st.subheader("📅 HISTORICAL")

hist = get_historical(sec, seg, inst)

if hist is not None:
    st.dataframe(hist.tail())
else:
    st.warning("No Data")

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

    return pd.DataFrame(data)

st.subheader("🕯 INTRADAY")

candle = get_intraday(sec, seg, inst)

if candle is not None:
    st.line_chart(candle["close"])
else:
    st.warning("No Data")

# =========================
# OPTION CHAIN
# =========================
@st.cache_data(ttl=300)
def get_expiry(sec):
    payload = {
        "UnderlyingScrip": int(sec),
        "UnderlyingSeg": "IDX_I"
    }

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

st.subheader("📊 OPTION CHAIN")

nifty_sec, _, _ = symbols["NIFTY"]

expiries = get_expiry(nifty_sec)

if expiries:
    selected_exp = st.selectbox("Select Expiry", expiries)

    chain = get_chain(nifty_sec, selected_exp)

    if chain:
        df = pd.DataFrame.from_dict(chain, orient="index")
        st.success(f"Strikes: {len(df)}")
        st.dataframe(df.head(20))
    else:
        st.warning("Chain Error")
else:
    st.warning("No Expiry Data")

# =========================
# DEBUG PANEL
# =========================
st.subheader("🛠 DEBUG")

st.write({
    "Token": "OK",
    "LTP": ltp,
    "Depth": depth is not None,
    "Historical": hist is not None,
    "Intraday": candle is not None,
    "Expiry": len(expiries) > 0
})
