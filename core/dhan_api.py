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
    """Make a POST request with rate limiting and automatic retries on 805."""
    global _last_call_time
    for attempt in range(retries):
        # Rate limit: ensure at least 3 seconds between calls
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
                st.error("❌ Token Expired / Invalid – Please regenerate your Dhan access token.")
                return None
            if "805" in str(data):
                st.warning(f"⚠️ Rate limit exceeded (attempt {attempt+1}/{retries}). Waiting 3 seconds...")
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

# -----------------------------
# EXPIRY LIST
# -----------------------------
@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_expiry_list(security_id):
    """
    Fetch all expiry dates for a given security ID (e.g., 13 for NIFTY, 25 for BANKNIFTY).
    Returns a list of strings in YYYY-MM-DD format.
    """
    url = f"{BASE_URL}/optionchain/expirylist"
    payload = {
        "UnderlyingScrip": int(security_id),
        "UnderlyingSeg": "IDX_I"          # Indices (NIFTY, BANKNIFTY) are in this segment
    }
    data = safe_post(url, payload)
    if not data or data.get("status") != "success":
        return []
    return data.get("data", [])

# -----------------------------
# VALID EXPIRIES (NIFTY = Tuesday, BANKNIFTY = Thursday)
# -----------------------------
def get_valid_expiries(security_id):
    """
    Returns only expiries that are on the correct weekday for the instrument:
    - NIFTY (security_id=13) → Tuesday (weekday 1)
    - BANKNIFTY (security_id=25) → Thursday (weekday 3)
    """
    all_expiries = get_expiry_list(security_id)
    if not all_expiries:
        return []
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

# -----------------------------
# OPTION CHAIN
# -----------------------------
@st.cache_data(ttl=5)  # Cache for 5 seconds – live data changes quickly
def get_option_chain(security_id, segment, expiry):
    """
    Fetch option chain for a given security, segment, and expiry date.
    segment should be 'IDX_I' for indices, 'NSE_FNO' for stocks.
    expiry must be in YYYY-MM-DD format (as returned by get_valid_expiries).
    """
    url = f"{BASE_URL}/optionchain"
    payload = {
        "UnderlyingScrip": int(security_id),
        "UnderlyingSeg": segment,
        "Expiry": expiry
    }
    return safe_post(url, payload)

# -----------------------------
# MARKET QUOTE (LTP)
# -----------------------------
@st.cache_data(ttl=2)  # Cache for 2 seconds (LTP can be faster)
def get_ltp(security_id, segment):
    """
    Get last traded price for a given instrument using the Market Quote API.
    """
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
    if data and "data" in data and len(data["data"]) > 0:
        return data["data"][0].get("lastPrice")
    return None

# -----------------------------
# UTILITY: MAP SEGMENT FOR OPTION CHAIN
# -----------------------------
def get_option_segment(symbol):
    """
    Return the correct segment for option chain based on instrument name.
    """
    if "NIFTY" in symbol.upper() or "BANKNIFTY" in symbol.upper():
        return "IDX_I"
    else:
        return "NSE_FNO"
