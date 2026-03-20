import time
import requests
import streamlit as st
from datetime import datetime

BASE_URL = "https://api.dhan.co/v2"
_last_call_time = 0


def get_headers():
    return {
        "access-token": st.secrets["ACCESS_TOKEN"],
        "client-id": st.secrets["CLIENT_ID"],
        "Content-Type": "application/json"
    }


def safe_post(url, payload, retries=2):
    """Make a POST request with rate limiting and retries."""
    global _last_call_time

    for attempt in range(retries):
        # Rate limit: wait if needed (1 request per 3 seconds)
        now = time.time()
        wait = max(0, 3 - (now - _last_call_time))
        if wait > 0:
            time.sleep(wait)

        try:
            res = requests.post(url, headers=get_headers(), json=payload, timeout=10)
            _last_call_time = time.time()
            data = res.json()

            # Handle known error codes
            if "808" in str(data):
                st.error("❌ Token Expired / Invalid – Please regenerate access token in Dhan.")
                return None
            if "805" in str(data):
                st.warning("⚠️ Rate limit exceeded. Waiting 3 seconds and retrying...")
                time.sleep(3)
                continue
            if data.get("status") == "failure":
                error_msg = data.get("remarks", {}).get("error_message", "Unknown error")
                st.error(f"❌ API Failure: {error_msg}")
                return None

            return data

        except requests.exceptions.Timeout:
            st.warning(f"Timeout (attempt {attempt+1}/{retries})")
            continue
        except Exception as e:
            st.error(f"Request error: {e}")
            return None

    st.error("❌ Max retries exceeded.")
    return None


@st.cache_data(ttl=300)  # cache expiry list for 5 minutes
def get_expiry_list(security_id=13):
    """
    Fetch expiry list for given security ID.
    security_id: 13 = NIFTY, 25 = BANKNIFTY
    Returns only valid expiries (NIFTY → Tuesday, BANKNIFTY → Thursday).
    """
    url = f"{BASE_URL}/optionchain/expirylist"
    payload = {
        "UnderlyingScrip": int(security_id),
        "UnderlyingSeg": "IDX_I"
    }
    data = safe_post(url, payload)
    if not data or data.get("status") != "success":
        st.error("Failed to fetch expiry list.")
        return []

    expiries = []
    target_weekday = 1 if security_id == 13 else 3  # 1=Tuesday, 3=Thursday
    for dt_str in data.get("data", []):
        try:
            dt = datetime.strptime(dt_str, "%Y-%m-%d")
            if dt.weekday() == target_weekday:
                expiries.append(dt_str)
        except:
            continue
    return sorted(expiries)


@st.cache_data(ttl=5)  # cache option chain for 5 seconds (live data)
def get_option_chain(security_id, expiry):
    """
    Fetch option chain for a given security ID and expiry date.
    expiry must be in YYYY-MM-DD format.
    """
    url = f"{BASE_URL}/optionchain"
    payload = {
        "UnderlyingScrip": int(security_id),
        "UnderlyingSeg": "IDX_I",
        "Expiry": expiry
    }
    return safe_post(url, payload)


# Optional: utility to check if market is open
def is_market_open():
    now = datetime.now()
    # Market hours: Monday–Friday, 9:15 AM – 3:30 PM
    if now.weekday() >= 5:   # weekend
        return False
    start = now.replace(hour=9, minute=15, second=0)
    end = now.replace(hour=15, minute=30, second=0)
    return start <= now <= end
