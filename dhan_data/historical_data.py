import requests
import streamlit as st
from core.token_manager import get_headers

BASE_URL = "https://api.dhan.co/v2"

@st.cache_data(ttl=30)
def get_historical_daily(security_id, segment):

    # 🔥 instrument mapping
    if segment == "IDX_I":
        instrument = "INDEX"
    elif segment == "NSE_EQ":
        instrument = "EQUITY"
    elif segment == "NSE_FNO":
        instrument = "FUTSTK"   # or OPTSTK
    else:
        instrument = "EQUITY"

    payload = {
        "securityId": str(security_id),
        "exchangeSegment": segment,
        "instrument": instrument,
        "expiryCode": 0,   # 🔥 IMPORTANT (cash = 0)
        "oi": False,
        "fromDate": "2025-03-01",
        "toDate": "2025-03-25"
    }

    res = requests.post(
        f"{BASE_URL}/charts/historical",
        headers=get_headers(),
        json=payload,
        timeout=10
    )

    print("STATUS:", res.status_code)
    print("RESPONSE:", res.text[:200])

    if res.status_code != 200:
        return {}

    data = res.json()

    return data if isinstance(data, dict) else {}
