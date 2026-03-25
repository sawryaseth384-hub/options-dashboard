import requests
import streamlit as st
from datetime import datetime, timedelta

from core.token_manager import get_headers

BASE_URL = "https://api.dhan.co/v2"


@st.cache_data(ttl=30)
def get_historical(security_id, segment, days=7):
    if segment == "IDX_I":
        instrument = "INDEX"
    elif segment == "NSE_EQ":
        instrument = "EQUITY"
    else:
        instrument = "EQUITY"

    to_date = datetime.now()
    from_date = to_date - timedelta(days=days)

    payload = {
        "securityId": str(security_id),
        "exchangeSegment": segment,
        "instrument": instrument,
        "expiryCode": 0,
        "oi": False,
        "fromDate": from_date.strftime("%Y-%m-%d"),
        "toDate": to_date.strftime("%Y-%m-%d"),
    }

    try:
        res = requests.post(
            f"{BASE_URL}/charts/historical",
            headers=get_headers(),
            json=payload,
            timeout=10,
        )

        if res.status_code != 200:
            return {}

        data = res.json()
        if not data or "open" not in data:
            return {}

        return data
    except Exception:
        return {}
