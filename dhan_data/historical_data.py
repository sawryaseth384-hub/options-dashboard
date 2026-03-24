import requests
from datetime import datetime, timedelta
import streamlit as st
import time
from core.token_manager import get_headers

BASE_URL = "https://api.dhan.co/v2"
_last_hist_call = 0

def get_historical(security_id, segment):
    global _last_hist_call
    now = time.time()
    wait = max(0, 1 - (now - _last_hist_call))
    if wait > 0:
        time.sleep(wait)
    _last_hist_call = time.time()

    # Use NSE_EQ for all (the chart endpoint works with NSE_EQ for both indices and stocks)
    exchange = "NSE_EQ"
    instrument = "INDEX" if segment in ["IDX_I", "I"] else "EQUITY"
    to_date = datetime.now()
    from_date = to_date - timedelta(days=1)
    payload = {
        "securityId": str(security_id),
        "exchangeSegment": exchange,
        "instrument": instrument,
        "interval": "5",
        "oi": False,
        "fromDate": from_date.strftime("%Y-%m-%d %H:%M:%S"),
        "toDate": to_date.strftime("%Y-%m-%d %H:%M:%S")
    }
    try:
        res = requests.post(f"{BASE_URL}/charts/intraday", headers=get_headers(), json=payload, timeout=10)
        data = res.json()
        if "data" not in data:
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
    except Exception as e:
        st.error(f"Historical data error: {e}")
        return []
