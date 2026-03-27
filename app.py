import logging
import os
from datetime import datetime, timedelta

import plotly.graph_objects as go
import streamlit as st

from dhan_auth import get_token
from core.dhan_v2 import (
    extract_ltp,
    get_depth,
    get_historical,
    get_intraday,
    get_ltp,
    get_option_chain,
)
from dhan_data.option_chain import get_expiry_list

_logger = logging.getLogger(__name__)

st.set_page_config(layout="wide", page_title="🚀 Dhan Trading Dashboard")
st.title("🚀 Dhan Trading Dashboard")

# ---------------- SYMBOL MAP ----------------
SECURITY_MAP = {
    "NIFTY": ("13", "NSE_INDEX"),
    "RELIANCE": ("2885", "NSE_EQ"),
}

# ---------------- DEBUG UI ----------------
st.subheader("🔐 Debug Info")

st.write("CLIENT_ID:", os.getenv("CLIENT_ID"))

try:
    token = get_token()
    st.write("TOKEN:", token[:10] + "...")
except Exception as e:
    st.write("TOKEN ERROR:", e)

# ---------------- HELPERS ----------------

def _retry_401(fn):
    try:
        return fn()
    except Exception as e:
        return {"error": str(e)}

def _extract_data_list(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("data", "result", "records", "candles"):
            val = payload.get(key)
            if isinstance(val, list):
                return val
    return None

def _show_error(data):
    if isinstance(data, dict) and data.get("error"):
        st.error(data["error"])
        return True
    return False

# ---------------- FETCHERS ----------------

def _fetch_ltp(security_id, segment):
    return _retry_401(lambda: get_ltp(security_id, segment))

def _fetch_option_chain(security_id, segment, expiry):
    return _retry_401(lambda: get_option_chain(security_id, segment=segment, expiry=expiry))

def _fetch_intraday(security_id, segment):
    return _retry_401(lambda: get_intraday(security_id, segment))

def _fetch_historical(security_id, segment):
    return _retry_401(lambda: get_historical(security_id, segment))

def _fetch_depth(security_id, segment):
    return _retry_401(lambda: get_depth(security_id, segment))

# ---------------- UI ----------------

symbol = st.selectbox("Select Symbol", list(SECURITY_MAP.keys()))
security_id, segment = SECURITY_MAP[symbol]

# ---------------- LTP ----------------

st.subheader("📈 Live Price")

with st.spinner("Loading LTP..."):
    ltp_data = _fetch_ltp(security_id, segment)

if _show_error(ltp_data):
    st.metric("LTP", "No Data")
else:
    try:
        ltp = extract_ltp(ltp_data)
        st.metric("LTP", f"{ltp:.2f}")
    except Exception as e:
        st.error(f"LTP parsing error: {e}")

# ---------------- EXPIRY ----------------

expiries = get_expiry_list(security_id, segment)
if isinstance(expiries, tuple):
    expiries, err = expiries
else:
    err = None
expiry = expiries[0] if expiries else None
if err or not expiry:
    st.error("Expiry API failed due to authentication or payload issue")
    st.stop()
# ---------------- TABS ----------------

tabs = st.tabs(["Option Chain", "Charts", "Market Depth", "Debug"])

# ---------------- OPTION CHAIN ----------------

with tabs[0]:
    st.subheader("📊 Option Chain")

    with st.spinner("Loading Option Chain..."):
        chain = _fetch_option_chain(security_id, segment, expiry)

    if _show_error(chain):
        st.info("Option chain unavailable")
    elif not chain:
        st.info("No data")
    else:
        data = chain.get("data", chain) if isinstance(chain, dict) else chain
        st.dataframe(data, use_container_width=True)

# ---------------- CHARTS ----------------

with tabs[1]:
    st.subheader("📉 Charts")

    timeframe = st.selectbox("Timeframe", ["1", "5", "15"], format_func=lambda x: f"{x}m")

    with st.spinner("Loading intraday..."):
        intraday = _fetch_intraday(security_id, segment)

    records = _extract_data_list(intraday)

    if records:
        try:
            fig = go.Figure(
                data=[
                    go.Candlestick(
                        x=[r[0] for r in records],
                        open=[r[1] for r in records],
                        high=[r[2] for r in records],
                        low=[r[3] for r in records],
                        close=[r[4] for r in records],
                    )
                ]
            )
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Chart error: {e}")
    else:
        st.info("No intraday data")

    st.divider()

    with st.spinner("Loading historical..."):
        hist = _fetch_historical(security_id, segment)

    hist_records = _extract_data_list(hist)

    if hist_records:
        st.dataframe(hist_records, use_container_width=True)
    else:
        st.info("No historical data")

# ---------------- DEPTH ----------------

with tabs[2]:
    st.subheader("📘 Market Depth")

    with st.spinner("Loading depth..."):
        depth = _fetch_depth(security_id, segment)

    if _show_error(depth):
        st.info("Depth unavailable")
    elif not depth:
        st.info("No data")
    else:
        st.json(depth)

# ---------------- DEBUG ----------------

with tabs[3]:
    st.subheader("🧪 Debug")

    st.write("Security ID:", security_id)
    st.write("Segment:", segment)
    st.write("Expiry:", expiry)
