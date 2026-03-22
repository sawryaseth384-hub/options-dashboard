import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import time

BASE_URL = "https://api.dhan.co/v2"

_last_expired_call = 0

def get_headers():
    return {
        "access-token": st.secrets["ACCESS_TOKEN"],
        "client-id": st.secrets["CLIENT_ID"],
        "Content-Type": "application/json"
    }

def get_expired_options(security_id, segment, option_type="CALL"):
    global _last_expired_call

    # Rate limit
    now = time.time()
    wait = max(0, 1 - (now - _last_expired_call))
    if wait > 0:
        time.sleep(wait)
    _last_expired_call = time.time()

    try:
        url = f"{BASE_URL}/charts/rollingoption"

        to_date = datetime.now()
        from_date = to_date - timedelta(days=5)

        # 🔥 FIX: instrument based on segment
        instrument = "OPTIDX" if segment == "IDX_I" else "OPTSTK"

        payload = {
            "exchangeSegment": "NSE_FNO",   # Always NSE_FNO for options
            "interval": "1",
            "securityId": int(security_id),
            "instrument": instrument,
            "expiryFlag": "WEEK",
            "expiryCode": 0,
            "strike": "ATM",
            "drvOptionType": option_type,   # CALL / PUT
            "requiredData": [
                "open", "high", "low", "close",
                "volume", "oi", "iv", "spot"
            ],
            "fromDate": from_date.strftime("%Y-%m-%d"),
            "toDate": to_date.strftime("%Y-%m-%d")
        }

        res = requests.post(url, headers=get_headers(), json=payload, timeout=10)
        raw = res.json()

        if not raw or "data" not in raw:
            return None

        key = "ce" if option_type == "CALL" else "pe"
        data = raw["data"].get(key)

        if not data:
            return None

        df = pd.DataFrame({
            "time": pd.to_datetime(data.get("timestamp", []), unit="s"),
            "open": data.get("open", []),
            "high": data.get("high", []),
            "low": data.get("low", []),
            "close": data.get("close", []),
            "volume": data.get("volume", []),
            "oi": data.get("oi", []),
            "iv": data.get("iv", []),
            "spot": data.get("spot", []),
            "strike": data.get("strike", [])
        })

        if df.empty:
            return None

        df = df.dropna()
        return df

    except Exception as e:
        st.error(f"Expired Option Error: {e}")
        return None
