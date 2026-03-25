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
st.title("🚀 MULTI SYMBOL TRADING DASHBOARD")

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
# SYMBOL MASTER
# =========================
symbols = {
    "NIFTY": (13, "IDX_I", "INDEX"),
    "BANKNIFTY": (25, "IDX_I", "INDEX"),
    "FINNIFTY": (27, "IDX_I", "INDEX"),
    "RELIANCE": (2885, "NSE_EQ", "EQUITY"),
    "TCS": (11536, "NSE_EQ", "EQUITY"),
}

selected_symbols = st.multiselect(
    "Select Symbols",
    list(symbols.keys()),
    default=["NIFTY", "BANKNIFTY", "RELIANCE"]
)

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
            res = requests.post(url, headers={
                "access-token": get_token(),
                "client-id": CLIENT_ID,
                "Content-Type": "application/json"
            }, json=payload, timeout=10)

            if res.status_code == 200:
                data = res.json()
                if data:
                    return data

        except:
            time.sleep(1)

    return None

# =========================
# DEPTH FUNCTION
# =========================
@st.cache_data(ttl=5)
def get_depth(sec, seg):
    payload = {seg: [int(sec)]}
    data = safe_post(f"{BASE_URL}/marketfeed/ltp", payload)

    if not data:
        return None

    try:
        d = data["data"][seg][str(sec)]
        return {
            "ltp": float(d.get("last_price", 0)),
            "high": float(d.get("high") or d.get("last_price", 0)),
            "low": float(d.get("low") or d.get("last_price", 0)),
        }
    except:
        return None

# =========================
# INTRADAY FUNCTION
# =========================
@st.cache_data(ttl=15)
def get_intraday(sec, seg, inst):
    payload = {
        "securityId": str(sec),
        "exchangeSegment": seg,
        "instrument": inst,
        "interval": "5",
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

    if "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"])
        df = df.set_index("datetime")

    return df

# =========================
# DASHBOARD GRID
# =========================
st.subheader("📊 LIVE MARKET")

cols = st.columns(len(selected_symbols))

for i, sym in enumerate(selected_symbols):
    sec, seg, inst = symbols[sym]

    with cols[i]:

        st.markdown(f"### {sym}")

        # LTP
        ltp = get_live_price()
        try:
            ltp = float(ltp)
        except:
            ltp = 0

        st.metric("LTP", round(ltp, 2) if ltp else "—")

        # Depth
        depth = get_depth(sec, seg)

        if depth:
            st.caption(f"H: {depth['high']} | L: {depth['low']}")
        else:
            st.caption("No depth")

        # Intraday Chart
        candle = get_intraday(sec, seg, inst)

        if candle is not None and not candle.empty:
            st.line_chart(candle["close"])
        else:
            st.write("No chart")

# =========================
# STATUS
# =========================
st.subheader("🛠 SYSTEM STATUS")

st.write({
    "WS": st.session_state.get("ws_started", False),
    "Symbols": selected_symbols,
})
