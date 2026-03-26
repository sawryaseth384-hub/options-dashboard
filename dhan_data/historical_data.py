import streamlit as st
from dhan_data.client import safe_post

BASE_URL = "https://api.dhan.co"

@st.cache_data(ttl=30)
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

    data, err = safe_post(f"{BASE_URL}/v2/charts/historical", payload, timeout=10)
    if err or not data:
        return {}
    if not isinstance(data, dict) or "open" not in data:
        return {}
    return data
