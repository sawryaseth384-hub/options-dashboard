import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, timedelta
from typing import Optional, Tuple, Any

# ✅ Token Manager
from core.token_manager import get_token

# ✅ WebSocket (assumes it runs in background and updates a global variable)
from dhan_data.live_market_feed import start_feed, get_live_price

# =========================
# CONFIG
# =========================
BASE_URL = "https://api.dhan.co/v2"

st.set_page_config(layout="wide")
st.title("🚀 Dhan Full Dashboard")

# =========================
# START WEBSOCKET (ONCE)
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
# HELPER FUNCTIONS
# =========================
def get_headers():
    """Return headers for API calls."""
    return {
        "access-token": get_token(),
        "client-id": st.secrets["CLIENT_ID"],
        "Content-Type": "application/json"
    }

def safe_post(url: str, payload: dict) -> Tuple[Optional[dict], Optional[str]]:
    """
    Make a POST request with error handling and minimal rate limiting.
    Returns (data, error_message).
    """
    try:
        res = requests.post(url, headers=get_headers(), json=payload, timeout=10)
        if res.status_code != 200:
            return None, f"HTTP {res.status_code}: {res.text[:200]}"

        data = res.json()
        # Check for Dhan error codes (e.g., token expired)
        if isinstance(data, dict) and data.get("code") == "808":
            return None, "Token expired"

        return data, None

    except Exception as e:
        return None, str(e)

# =========================
# CACHED API CALLS (with TTL)
# =========================
@st.cache_data(ttl=3600)  # cache for 1 hour
def get_expiry(sec: int) -> Tuple[list, Optional[str]]:
    """Get list of expiry dates for an index."""
    payload = {
        "UnderlyingScrip": int(sec),
        "UnderlyingSeg": "IDX_I"
    }
    data, err = safe_post(f"{BASE_URL}/optionchain/expirylist", payload)
    if err:
        return [], err
    if not data or data.get("status") != "success":
        return [], "Invalid response"
    return data.get("data", []), None

@st.cache_data(ttl=300)  # cache for 5 minutes (intraday changes)
def get_historical(sec: int, seg: str, inst: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """Get historical data (last 10 days)."""
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
        return None, "No data or unexpected format"
    return pd.DataFrame(data), None

@st.cache_data(ttl=60)  # cache for 1 minute (intraday updates often)
def get_intraday(sec: int, seg: str, inst: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """Get intraday candle data (today, 1‑minute bars)."""
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
    if not data:
        return None, "No data"
    return pd.DataFrame(data), None

def get_depth(sec: int, seg: str) -> Tuple[Optional[dict], Optional[str]]:
    """
    Get market depth (LTP, high, low, open) for a security.
    This is not cached because we want live values on refresh.
    """
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
    except (KeyError, TypeError):
        return None, "Unexpected response structure"

def get_chain(sec: int, expiry: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """Get option chain for a given expiry."""
    payload = {
        "UnderlyingScrip": int(sec),
        "UnderlyingSeg": "IDX_I",
        "Expiry": expiry
    }
    data, err = safe_post(f"{BASE_URL}/optionchain", payload)
    if err:
        return None, err
    if not data or data.get("status") != "success":
        return None, "Invalid response"
    chain_data = data.get("data", {}).get("oc")
    if not chain_data:
        return None, "No chain data"
    df = pd.DataFrame(chain_data).T
    return df, None

# =========================
# SESSION STATE INIT
# =========================
if "data" not in st.session_state:
    st.session_state.data = {
        "depth": None,
        "historical": None,
        "candle": None,
        "expiries": [],
        "chain": None,
        "last_refresh": datetime.min,
        "selected_expiry": None
    }

# =========================
# SYMBOLS (hardcoded)
# =========================
symbols = {
    "NIFTY": (13, "IDX_I", "INDEX"),
    "RELIANCE": (2885, "NSE_EQ", "EQUITY"),
}

# =========================
# SIDEBAR – CONTROLS
# =========================
with st.sidebar:
    st.header("📊 Controls")
    refresh = st.button("🔄 Refresh All Data")
    selected_symbol = st.selectbox("Select Symbol", list(symbols.keys()), key="symbol")
    sec, seg, inst = symbols[selected_symbol]

    # Option chain selector (only for NIFTY)
    if selected_symbol == "NIFTY":
        with st.spinner("Fetching expiry list..."):
            expiries, e_err = get_expiry(sec)
        if expiries:
            selected_expiry = st.selectbox("Select Expiry", expiries, key="expiry")
            st.session_state.data["selected_expiry"] = selected_expiry
        else:
            st.error(f"Expiry error: {e_err}")
            selected_expiry = None
    else:
        selected_expiry = None
        st.info("Option chain only available for NIFTY")

# =========================
# LIVE LTP (via WebSocket)
# =========================
st.subheader("📈 LIVE LTP")
ltp = get_live_price()
if ltp > 0:
    st.success(f"🔥 Current LTP: {round(ltp, 2)}")
else:
    st.warning("⏳ Waiting for live data...")

# =========================
# REFRESH LOGIC
# =========================
if refresh or st.session_state.data["last_refresh"] == datetime.min:
    with st.spinner("Fetching latest data..."):
        depth, d_err = get_depth(sec, seg)
        if depth:
            st.session_state.data["depth"] = depth
        else:
            st.session_state.data["depth"] = None
            st.error(f"Depth error: {d_err}")

        hist, h_err = get_historical(sec, seg, inst)
        if hist is not None:
            st.session_state.data["historical"] = hist
        else:
            st.session_state.data["historical"] = None
            st.warning(f"Historical error: {h_err}")

        candle, c_err = get_intraday(sec, seg, inst)
        if candle is not None:
            st.session_state.data["candle"] = candle
        else:
            st.session_state.data["candle"] = None
            st.warning(f"Candle error: {c_err}")

        # Option chain if NIFTY and expiry selected
        if selected_symbol == "NIFTY" and selected_expiry:
            chain, ch_err = get_chain(sec, selected_expiry)
            if chain is not None:
                st.session_state.data["chain"] = chain
            else:
                st.session_state.data["chain"] = None
                st.warning(f"Chain error: {ch_err}")

        st.session_state.data["last_refresh"] = datetime.now()
        st.success("Data refreshed!")

# =========================
# DISPLAY SECTIONS
# =========================
# Market Depth
st.subheader("📊 MARKET DEPTH")
depth = st.session_state.data["depth"]
if depth:
    col1, col2, col3 = st.columns(3)
    col1.metric("LTP", depth["LTP"])
    col2.metric("High", depth["High"])
    col3.metric("Low", depth["Low"])
    st.metric("Open", depth["Open"])
else:
    st.info("No depth data available. Use 'Refresh All Data'.")

# Historical Data
st.subheader("📅 HISTORICAL (Last 10 days)")
hist = st.session_state.data["historical"]
if hist is not None:
    st.dataframe(hist.tail())
else:
    st.info("No historical data. Click refresh.")

# Intraday Candles
st.subheader("🕯 INTRADAY CANDLES (1‑minute)")
candle = st.session_state.data["candle"]
if candle is not None and "close" in candle:
    st.line_chart(candle["close"])
elif candle is not None:
    st.write("Candle data available but 'close' column missing:")
    st.dataframe(candle.head())
else:
    st.info("No intraday data. Click refresh.")

# Option Chain (if NIFTY)
if selected_symbol == "NIFTY":
    st.subheader("📊 OPTION CHAIN")
    chain = st.session_state.data["chain"]
    if chain is not None:
        st.success(f"Strikes: {len(chain)}")
        st.dataframe(chain.head(20))
    else:
        st.info("No option chain data. Ensure expiry is selected and refresh.")

# =========================
# DEBUG PANEL (optional)
# =========================
with st.expander("🛠 Debug Panel"):
    st.write("Token status:", "✅" if get_token() else "❌")
    st.write("Live LTP:", round(ltp, 2) if ltp > 0 else "N/A")
    st.write("Depth:", "OK" if st.session_state.data["depth"] else "FAIL")
    st.write("Historical:", "OK" if st.session_state.data["historical"] is not None else "FAIL")
    st.write("Candle:", "OK" if st.session_state.data["candle"] is not None else "FAIL")
    if selected_symbol == "NIFTY":
        st.write("Expiry list:", "OK" if expiries else "FAIL")
        st.write("Option Chain:", "OK" if st.session_state.data["chain"] is not None else "FAIL")
    st.write("Last refresh:", st.session_state.data["last_refresh"].strftime("%H:%M:%S"))
