import time
import requests
import streamlit as st
from core.token_manager import get_headers

BASE_URL = "https://api.dhan.co/v2"

# GLOBAL RATE CONTROL
_last_call_time = 0

def safe_post(url, payload, retries=2):
    global _last_call_time

    for attempt in range(retries):
        now = time.time()

        # 🔥 RATE LIMIT CONTROL
        wait = max(0, 1 - (now - _last_call_time))
        if wait > 0:
            time.sleep(wait)

        try:
            res = requests.post(
                url,
                headers=get_headers(),
                json=payload,
                timeout=10
            )

            _last_call_time = time.time()

            if res.status_code != 200:
                print("❌ HTTP:", res.status_code, res.text)
                return {}

            data = res.json()

            return data.get("data", {})

        except Exception as e:
            print("❌ Request Error:", e)
            time.sleep(1)

    return {}


# =========================
# 📊 HISTORICAL (FINAL)
# =========================
@st.cache_data(ttl=10)
def get_historical(security_id, segment):

    payload = {
        "securityId": str(security_id),
        "exchangeSegment": segment,
        "instrument": "EQUITY",
        "interval": "1",
        "oi": False,
        "fromDate": "2025-03-25 09:15:00",
        "toDate": "2025-03-25 15:30:00"
    }

    return safe_post(f"{BASE_URL}/charts/intraday", payload)
