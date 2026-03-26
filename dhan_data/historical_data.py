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
    if "open" not in data and "o" in data:
        data = data.copy()
        data["open"] = data.get("o")
        data["high"] = data.get("high") or data.get("h")
        data["low"] = data.get("low") or data.get("l")
        data["close"] = data.get("close") or data.get("c")
        data["volume"] = data.get("volume") or data.get("v")
        data["timestamp"] = data.get("timestamp") or data.get("t")
    return data


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
    if not data or not any(key in data for key in ("open", "o")):
        return {}
    return data
