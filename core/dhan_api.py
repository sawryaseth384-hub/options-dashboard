import time
import requests
import streamlit as st
from datetime import datetime

BASE_URL = "https://api.dhan.co/v2"
_last_call_time = 0


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
# ⚡ SAFE POST (RATE SAFE)
# =========================
def safe_post(url, payload, retries=2):
    global _last_call_time

    for attempt in range(retries):
        now = time.time()
        wait = max(0, 3 - (now - _last_call_time))

        if wait > 0:
            time.sleep(wait)

        try:
            res = requests.post(url, headers=get_headers(), json=payload, timeout=10)
            _last_call_time = time.time()

            data = res.json()

            # 🔴 TOKEN ERROR
            if "808" in str(data):
                st.error("❌ Token Expired / Invalid")
                return None

            # ⚠️ RATE LIMIT
            if "805" in str(data):
                st.warning(f"⚠️ Rate limit hit (attempt {attempt+1})")
                time.sleep(3)
                continue

            # ❌ API FAILURE
            if data.get("status") == "failure":
                msg = data.get("remarks", {}).get("error_message", "Unknown error")
                st.error(f"❌ API Error: {msg}")
                return None

            return data

        except requests.exceptions.Timeout:
            st.warning(f"Timeout retry {attempt+1}")
            continue

        except Exception as e:
            st.error(f"Request Error: {e}")
            return None

    st.error("❌ Max retries exceeded")
    return None


# =========================
# 📅 EXPIRY LIST
# =========================
@st.cache_data(ttl=300)
def get_expiry_list(security_id):
    url = f"{BASE_URL}/optionchain/expirylist"

    payload = {
        "UnderlyingScrip": int(security_id),
        "UnderlyingSeg": "IDX_I"
    }

    data = safe_post(url, payload)

    if not data or data.get("status") != "success":
        return []

    return data.get("data", [])


# =========================
# 🎯 VALID EXPIRIES
# =========================
def get_valid_expiries(security_id):
    all_expiries = get_expiry_list(security_id)

    if not all_expiries:
        return []

    # NIFTY = Tuesday, BANKNIFTY = Thursday
    target_weekday = 1 if security_id == 13 else 3

    valid = []

    for dt_str in all_expiries:
        try:
            dt = datetime.strptime(dt_str, "%Y-%m-%d")
            if dt.weekday() == target_weekday:
                valid.append(dt_str)
        except:
            continue

    return sorted(valid)


# =========================
# 📊 OPTION CHAIN
# =========================
@st.cache_data(ttl=5)
def get_option_chain(security_id, segment, expiry):
    url = f"{BASE_URL}/optionchain"

    payload = {
        "UnderlyingScrip": int(security_id),
        "UnderlyingSeg": segment,
        "Expiry": expiry
    }

    return safe_post(url, payload)


# =========================
# 💰 LTP (FIXED)
# =========================
@st.cache_data(ttl=2)
def get_ltp(security_id, segment):
    url = f"{BASE_URL}/marketquote"

    payload = {
        "instruments": [
            {
                "exchangeSegment": segment,
                "securityId": int(security_id)
            }
        ]
    }

    data = safe_post(url, payload)

    try:
        return data["data"][segment][str(security_id)]["last_price"]
    except:
        return None


# =========================
# 📈 HISTORICAL DATA (NEW)
# =========================
def get_historical_data(security_id):
    url = f"{BASE_URL}/charts/intraday"

    payload = {
        "securityId": str(security_id),
        "exchangeSegment": "IDX_I",
        "instrument": "INDEX",
        "interval": "5",
        "fromDate": "2026-03-20",
        "toDate": "2026-03-21"
    }

    return safe_post(url, payload)


# =========================
# 🔄 SEGMENT HELPER
# =========================
def get_option_segment(symbol):
    symbol = symbol.upper()

    if "NIFTY" in symbol or "BANKNIFTY" in symbol:
        return "IDX_I"

    return "NSE_FNO"
