import streamlit as st
from dhan_data.client import safe_post

BASE_URL = "https://api.dhan.co/v2"

@st.cache_data(ttl=30)
def _normalize_historical_payload(payload):
    if not isinstance(payload, dict):
        return {}
    data = payload.get("data") if "data" in payload else payload
    if isinstance(data, dict) and isinstance(data.get("candles"), dict):
        data = data.get("candles")
    if not isinstance(data, dict):
        return {}
    if "open" not in data and "o" not in data:
        return {}
    return {
        "open": data.get("open", data.get("o")),
        "high": data.get("high", data.get("h")),
        "low": data.get("low", data.get("l")),
        "close": data.get("close", data.get("c")),
        "volume": data.get("volume", data.get("v")),
        "timestamp": data.get("timestamp", data.get("t"))
    }


def get_historical(security_id, segment, from_date="2025-03-01", to_date="2025-03-25"):

    # 🔥 correct instrument mapping
    if segment == "IDX_I":
        instrument = "INDEX"
    elif segment == "NSE_EQ":
        instrument = "EQUITY"
    else:
        instrument = "EQUITY"

    payload = {
        "securityId": str(security_id),
        "exchangeSegment": segment,
        "instrument": instrument,
        "expiryCode": 0,
        "oi": False,
        "fromDate": from_date,
        "toDate": to_date
    }

    data, err = safe_post(f"{BASE_URL}/charts/historical", payload, timeout=10)
    if err or not data:
        return {}
    data = _normalize_historical_payload(data)
    if not data or "open" not in data:
        return {}
    return data
