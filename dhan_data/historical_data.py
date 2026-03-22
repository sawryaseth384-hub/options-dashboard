import requests
from datetime import datetime, timedelta
import streamlit as st
import time

_last_hist_call = 0

def get_historical(security_id, segment):
    global _last_hist_call

    # Rate limit
    now = time.time()
    wait = max(0, 1 - (now - _last_hist_call))
    if wait > 0:
        time.sleep(wait)
    _last_hist_call = time.time()

    url = "https://api.dhan.co/v2/charts/intraday"

    to_date = datetime.now()
    from_date = to_date - timedelta(days=3)

    # 🔥 FIX: Determine exchange and instrument based on segment
    if segment == "IDX_I":
        exchange = "NSE_EQ"
        instrument = "INDEX"
    elif segment == "D":
        exchange = "NSE_EQ"
        instrument = "EQUITY"
    else:
        exchange = segment   # e.g., "NSE_FNO" (rare)
        instrument = "EQUITY"

    payload = {
        "securityId": str(security_id),
        "exchangeSegment": exchange,
        "instrument": instrument,
        "interval": "5",
        "oi": False,
        "fromDate": from_date.strftime("%Y-%m-%d %H:%M:%S"),
        "toDate": to_date.strftime("%Y-%m-%d %H:%M:%S")
    }

    headers = {
        "access-token": st.secrets["ACCESS_TOKEN"],
        "client-id": st.secrets["CLIENT_ID"],
        "Content-Type": "application/json"
    }

    res = requests.post(url, headers=headers, json=payload)
    data = res.json()

    if "errorCode" in data:
        st.error(data.get("errorMessage"))
        return []

    # 🔥 FIX: Check for "data" key
    if "data" not in data or not data["data"]:
        return []

    d = data["data"]
    if "open" not in d:
        return []

    result = []
    for i in range(len(d["timestamp"])):
        result.append({
            "time": d["timestamp"][i],
            "open": d["open"][i],
            "high": d["high"][i],
            "low": d["low"][i],
            "close": d["close"][i]
        })
    return result
