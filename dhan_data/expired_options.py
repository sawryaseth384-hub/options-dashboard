import requests
import pandas as pd
import streamlit as st

BASE_URL = "https://api.dhan.co/v2"


# =========================
# 🔐 HEADERS
# =========================
def get_headers():
    return {
        "access-token": st.secrets["ACCESS_TOKEN"],
        "client-id": st.secrets["CLIENT_ID"],
        "Content-Type": "application/json"
    }


# =========================
# 📊 GET EXPIRED OPTION DATA
# =========================
def get_expired_options(security_id=13, option_type="CALL"):
    try:
        url = f"{BASE_URL}/charts/rollingoption"

        payload = {
            "exchangeSegment": "NSE_FNO",
            "interval": "1",
            "securityId": security_id,
            "instrument": "OPTIDX",
            "expiryFlag": "WEEK",
            "expiryCode": 0,
            "strike": "ATM",
            "drvOptionType": option_type,
            "requiredData": [
                "open", "high", "low", "close",
                "volume", "oi", "iv", "spot"
            ],
            "fromDate": "2024-01-01",
            "toDate": "2024-01-05"
        }

        res = requests.post(url, headers=get_headers(), json=payload)
        data = res.json()

        if "data" not in data:
            st.error("❌ No data")
            return None

        ce = data["data"].get("ce")

        if not ce:
            return None

        df = pd.DataFrame({
            "time": pd.to_datetime(ce["timestamp"], unit="s"),
            "open": ce.get("open", []),
            "high": ce.get("high", []),
            "low": ce.get("low", []),
            "close": ce.get("close", []),
            "volume": ce.get("volume", []),
            "oi": ce.get("oi", []),
            "iv": ce.get("iv", []),
            "spot": ce.get("spot", []),
            "strike": ce.get("strike", [])
        })

        df = df.dropna()

        return df

    except Exception as e:
        st.error(f"Expired Option Error: {e}")
        return None
