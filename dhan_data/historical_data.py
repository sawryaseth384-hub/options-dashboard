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


def get_historical_data(security_id, segment):

    try:
        url = f"{BASE_URL}/charts/intraday"

        to_date = datetime.now()
        from_date = to_date - timedelta(days=1)

        payload = {
            "securityId": str(security_id),
            "exchangeSegment": segment,
            "instrument": "INDEX",   # 🔥 NIFTY/BANKNIFTY
            "interval": "5",
            "oi": False,
            "fromDate": from_date.strftime("%Y-%m-%d %H:%M:%S"),
            "toDate": to_date.strftime("%Y-%m-%d %H:%M:%S")
        }

        res = requests.post(url, headers=get_headers(), json=payload)
        data = res.json()

        # 🔥 DEBUG PRINT
        st.write("RAW DATA:", data)

        # ✅ CHECK सही key
        if "open" not in data:
            st.error("❌ API data not received properly")
            return None

        df = pd.DataFrame({
            "datetime": pd.to_datetime(data["timestamp"], unit="s"),
            "open": data["open"],
            "high": data["high"],
            "low": data["low"],
            "close": data["close"],
            "volume": data["volume"]
        })

        return df

    except Exception as e:
        st.error(f"Error: {e}")
        return None
