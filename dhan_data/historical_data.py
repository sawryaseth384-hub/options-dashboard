import streamlit as st
from dhan_data.client import normalize_exchange_segment, sdk_historical_minute_charts

@st.cache_data(ttl=30)
def _normalize_historical_response(payload):
    """Normalize v2 historical responses into standard OHLC arrays."""
    if not isinstance(payload, dict):
        return {}
    data = payload.get("data") if "data" in payload else payload
    if isinstance(data, dict) and "candles" in data and isinstance(data["candles"], dict):
        data = data["candles"]
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

    segment = normalize_exchange_segment(segment)
    instrument = "INDEX" if segment == "NSE_INDEX" else "EQUITY"

    data, err = sdk_historical_minute_charts(
        security_id,
        segment,
        instrument,
        from_date,
        to_date,
        time_frame=5,
    )
    if err or not data:
        return {}
    data = _normalize_historical_response(data)
    if not data or "open" not in data:
        return {}
    return data
