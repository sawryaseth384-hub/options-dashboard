import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

BASE_URL = "https://api.dhan.co/v2"

def get_headers():
    return {
        "access-token": st.secrets["ACCESS_TOKEN"],
        "client-id": st.secrets["CLIENT_ID"],
        "Content-Type": "application/json"
    }

def get_historical(security_id, segment):

    try:
        url = f"{BASE_URL}/charts/intraday"

        to_date = datetime.now()
        from_date = to_date - timedelta(days=1)

        payload = {
            "securityId": int(security_id),
            "exchangeSegment": segment,
            "interval": "5",
            "oi": False,
            "fromDate": from_date.strftime("%Y-%m-%d %H:%M:%S"),
            "toDate": to_date.strftime("%Y-%m-%d %H:%M:%S")
        }

        res = requests.post(url, headers=get_headers(), json=payload, timeout=10)
        raw = res.json()

        # 🔍 DEBUG
        if st.sidebar.checkbox("Show Historical Debug"):
            st.write("RAW HIST:", raw)

        # ✅ HANDLE BOTH CASES
        data = raw.get("data", raw)

        # ❌ अगर open नहीं है → return
        if "open" not in data:
            return None

        df = pd.DataFrame({
            "time": pd.to_datetime(data["timestamp"], unit="s"),
            "open": data["open"],
            "high": data["high"],
            "low": data["low"],
            "close": data["close"],
            "volume": data.get("volume", [0]*len(data["open"]))
        })

        if df.empty:
            return None

        return df

    except Exception as e:
        st.error(f"Historical Error: {e}")
        return None
