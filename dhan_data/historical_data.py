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

    # 🔥 FIXED EXCHANGE + INSTRUMENT
    if segment == "IDX_I":
        exchange = "IDX_I"
        instrument = "INDEX"
    else:
        exchange = "NSE_EQ"
        instrument = "EQUITY"

    to_date = datetime.now()
    from_date = to_date - timedelta(days=3)

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
        res = requests.post(
            f"{BASE_URL}/charts/intraday",
            headers=get_headers(),
            json=payload,
            timeout=10
        )

        data = res.json()

        # 🔍 DEBUG (important)
        if "data" not in data or not data["data"]:
            st.warning(f"No historical data for {security_id}")
            return []

        d = data["data"]

        if "timestamp" not in d:
            st.warning("Invalid data format")
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
