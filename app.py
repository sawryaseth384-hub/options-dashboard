import logging
import os
from datetime import datetime, timedelta

import plotly.graph_objects as go
import streamlit as st

from dhan_auth import get_headers, get_token, refresh_token
from core.dhan_v2 import (
    extract_ltp,
    get_depth,
    get_historical,
    get_intraday,
    get_ltp,
    get_option_chain,
)

_logger = logging.getLogger(__name__)
st.set_page_config(layout="wide", page_title="🚀 Dhan Trading Dashboard")

SECURITY_MAP = {
    "NIFTY": ("13", "NSE_INDEX", "INDEX"),
    "RELIANCE": ("2885", "NSE_EQ", "EQUITY"),
}

# ---------- Helpers ----------

def _get_secret(key: str) -> str:
    try:
        val = st.secrets.get(key)
        if val:
            return str(val).strip()
    except Exception:
        pass
    return os.getenv(key, "").strip()

def _show_credential_status() -> bool:
    client_id = _get_secret("CLIENT_ID")
    pin = _get_secret("DHAN_PIN")
    totp_secret = _get_secret("TOTP_SECRET")

    st.sidebar.subheader("Credentials")
    st.sidebar.write("CLIENT_ID loaded ✅" if client_id else "CLIENT_ID missing ❌")
    st.sidebar.write("TOTP enabled ✅" if totp_secret else "TOTP missing ❌")
    st.sidebar.write("Auto token system active ✅")

    if not client_id or not pin or not totp_secret:
        st.error(
            "Missing credentials. Set CLIENT_ID, DHAN_PIN, and TOTP_SECRET in Streamlit secrets or environment variables."
        )
        st.code(
            'CLIENT_ID = "your_client_id"\nDHAN_PIN = "your_pin"\nTOTP_SECRET = "your_totp_secret"',
            language="toml",
        )
        st.info("Copy .streamlit/secrets.toml.example to .streamlit/secrets.toml, then reload this page.")
        return False
    return True

def _retry_401(fn, *args, **kwargs):
    resp = fn(*args, **kwargs)
    if isinstance(resp, dict) and resp.get("error"):
        return resp
    if getattr(resp, "status_code", None) == 401:
        refresh_token(force=True)
        resp = fn(*args, **kwargs)
    return resp

def _extract_data_list(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("data", "result", "records", "candles"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    return None

def _show_error(payload):
    if isinstance(payload, dict) and payload.get("error"):
        st.error(payload["error"])
        return True
    return False

# ---------- Validation ----------

def _validate_historical(security_id, segment, instrument, from_date, to_date):
    errors = []
    if not security_id:
        errors.append("securityId required")
    if segment not in ("NSE_EQ", "NSE_INDEX"):
        errors.append("exchangeSegment must be NSE_EQ or NSE_INDEX")
    if instrument not in ("EQUITY", "INDEX"):
        errors.append("instrument must be EQUITY or INDEX")
    if not from_date or not to_date:
        errors.append("fromDate and toDate required")
    if errors:
        return None, "; ".join(errors)
    return {
        "securityId": str(security_id),
        "exchangeSegment": segment,
        "instrument": instrument,
        "fromDate": from_date,
        "toDate": to_date,
    }, None

def _validate_intraday(security_id, segment, instrument, interval="1"):
    errors = []
    if not security_id:
        errors.append("securityId required")
    if segment not in ("NSE_EQ", "NSE_INDEX"):
        errors.append("exchangeSegment must be NSE_EQ or NSE_INDEX")
    if instrument not in ("EQUITY", "INDEX"):
        errors.append("instrument must be EQUITY or INDEX")
    if interval not in ("1", "5", "15"):
        errors.append("interval must be 1, 5, or 15")
    if errors:
        return None, "; ".join(errors)
    return {
        "securityId": str(security_id),
        "exchangeSegment": segment,
        "instrument": instrument,
        "interval": interval,
    }, None

def _validate_option_chain(security_id, expiry):
    errors = []
    if not security_id:
        errors.append("UnderlyingScrip required")
    if expiry is None:
        errors.append("Expiry required")
    if errors:
        return None, "; ".join(errors)
    return {
        "UnderlyingScrip": int(security_id),
        "UnderlyingSeg": "IDX_I",
        "Expiry": expiry,
    }, None

# ---------- Cached fetchers (fresh token inside) ----------

@st.cache_data(ttl=5, show_spinner=False)
def _fetch_ltp(security_id, segment):
    return _retry_401(lambda: get_ltp(security_id, segment))

@st.cache_data(ttl=5, show_spinner=False)
def _fetch_option_chain(security_id, segment):
    data = _retry_401(lambda: get_option_chain(security_id, exchange_segment=segment))
    return data

@st.cache_data(ttl=5, show_spinner=False)
def _fetch_intraday(payload):
    return _retry_401(lambda: get_intraday(**payload))

@st.cache_data(ttl=5, show_spinner=False)
def _fetch_historical(payload):
    return _retry_401(lambda: get_historical(**payload))

@st.cache_data(ttl=5, show_spinner=False)
def _fetch_depth(security_id, segment):
    return _retry_401(lambda: get_depth(security_id, segment))

# ---------- UI ----------

if not _show_credential_status():
    st.stop()

symbol = st.selectbox("Select Symbol", list(SECURITY_MAP.keys()))
security_id, segment, instrument = SECURITY_MAP[symbol]

# Top LTP and overview
with st.spinner("Loading live quote..."):
    ltp_data = _fetch_ltp(security_id, segment)

ltp_value = None
change_pct = None
high = None
low = None
if not _show_error(ltp_data):
    try:
        ltp_value = extract_ltp(ltp_data)
        high = ltp_data.get("high") if isinstance(ltp_data, dict) else None
        low = ltp_data.get("low") if isinstance(ltp_data, dict) else None
        change_pct = ltp_data.get("change") or ltp_data.get("pChange")
    except Exception as exc:
        _logger.exception("Failed to parse LTP: %s", exc)
        st.error(f"LTP parsing failed: {exc}")

col_a, col_b, col_c, col_d = st.columns(4)
col_a.metric("LTP", "No Data" if ltp_value is None else f"{ltp_value:.2f}")
col_b.metric("Change %", "---" if change_pct is None else f"{change_pct:.2f}%")
col_c.metric("High", "---" if high is None else f"{high:.2f}")
col_d.metric("Low", "---" if low is None else f"{low:.2f}")

tabs = st.tabs(["Option Chain", "Charts", "Market Depth", "Debug"])

# ----- Option Chain Tab -----
with tabs[0]:
    with st.spinner("Loading option chain..."):
        chain = _fetch_option_chain(security_id, segment)
    if _show_error(chain):
        st.info("Option chain unavailable.")
    elif not chain:
        st.info("No option chain data available.")
    else:
        df = chain if not isinstance(chain, dict) else chain.get("data", chain)
        if isinstance(df, list):
            st.dataframe(df, use_container_width=True)
        else:
            st.write(df)

# ----- Charts Tab -----
with tabs[1]:
    timeframe = st.selectbox("Timeframe", ["1", "5", "15"], format_func=lambda x: f"{x}m")
    today = datetime.utcnow().date()
    from_date = (today - timedelta(days=5)).isoformat()
    to_date = today.isoformat()

    intraday_payload, err_intr = _validate_intraday(security_id, segment, instrument, interval=timeframe)
    historical_payload, err_hist = _validate_historical(
        security_id, segment, instrument, from_date, to_date
    )

    if err_intr:
        st.error(err_intr)
    else:
        with st.spinner("Loading intraday..."):
            intraday_data = _fetch_intraday(intraday_payload)
        records = _extract_data_list(intraday_data)
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
                            name="Price",
                        )
                    ]
                )
                st.plotly_chart(fig, use_container_width=True)
            except Exception as exc:
                st.error(f"Failed to plot intraday: {exc}")
        else:
            st.info("No intraday data available.")

    st.divider()
    if err_hist:
        st.error(err_hist)
    else:
        with st.spinner("Loading historical..."):
            historical_data = _fetch_historical(historical_payload)
        h_records = _extract_data_list(historical_data)
        if h_records:
            st.dataframe(h_records, use_container_width=True)
        else:
            st.info("No historical data available.")

# ----- Market Depth Tab -----
with tabs[2]:
    with st.spinner("Loading market depth..."):
        depth_data = _fetch_depth(security_id, segment)
    if _show_error(depth_data):
        st.info("Market depth unavailable.")
    elif not depth_data:
        st.info("No market depth data available.")
    else:
        bids = depth_data.get("bids") or []
        asks = depth_data.get("asks") or []
        st.markdown("**Bids**")
        st.dataframe(bids, use_container_width=True)
        st.markdown("**Asks**")
        st.dataframe(asks, use_container_width=True)

# ----- Debug Tab -----
with tabs[3]:
    st.json(
        {
            "ltp_payload": {"security_id": security_id, "segment": segment},
            "intraday_payload": intraday_payload,
            "historical_payload": historical_payload,
            "option_chain_expiry": (chain or {}).get("selected_expiry") if isinstance(chain, dict) else None,
        }
    )
    st.write("Headers sample (masked):")
    try:
        hdrs = get_headers()
        hdrs_masked = {k: (v[:4] + "..." if isinstance(v, str) else v) for k, v in hdrs.items()}
        st.json(hdrs_masked)
    except Exception as exc:
        st.error(f"Header fetch failed: {exc}")
