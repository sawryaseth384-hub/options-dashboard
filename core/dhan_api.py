import requests
import streamlit as st
from datetime import datetime, timedelta

BASE_URL = "https://api.dhan.co/v2"

# =========================
# 🔐 HEADERS
# =========================
def headers():
    return {
        "access-token": st.secrets["ACCESS_TOKEN"],
        "client-id": st.secrets["CLIENT_ID"],
        "Content-Type": "application/json"
    }

# =========================
# 🎯 SYMBOL HANDLER
# =========================
def get_symbol_info(symbol):

    symbol = symbol.upper()

    if symbol == "NIFTY":
        return 13, "IDX_I"

    if symbol == "BANKNIFTY":
        return 25, "IDX_I"

    if symbol == "FINNIFTY":
        return 27, "IDX_I"

    return None, None

# =========================
# 💰 LTP
# =========================
def fetch_ltp(security_id, segment):

    url = f"{BASE_URL}/marketfeed/ltp"

    payload = {
        "IDX_I": [],
        "NSE_FNO": [],
        "NSE_EQ": []
    }

    if segment == "IDX_I":
        payload["IDX_I"].append(int(security_id))
    else:
        payload["NSE_FNO"].append(int(security_id))

    try:
        res = requests.post(url, headers=headers(), json=payload)
        data = res.json()

        return data["data"][segment][str(security_id)]["last_price"]

    except:
        return 0

# =========================
# 📅 EXPIRY
# =========================
def fetch_expiry(security_id, segment):

    url = f"{BASE_URL}/optionchain/expirylist"

    payload = {
        "UnderlyingScrip": int(security_id),
        "UnderlyingSeg": segment
    }

    try:
        res = requests.post(url, headers=headers(), json=payload)
        data = res.json()

        if data.get("status") == "success":
            return data.get("data", [])

    except:
        pass

    return []

# =========================
# 📊 OPTION CHAIN
# =========================
def fetch_option_chain(security_id, segment, expiry):

    url = f"{BASE_URL}/optionchain"

    payload = {
        "UnderlyingScrip": int(security_id),
        "UnderlyingSeg": segment,
        "Expiry": expiry
    }

    try:
        res = requests.post(url, headers=headers(), json=payload)
        return res.json()
    except:
        return {}

# =========================
# 📈 HISTORICAL
# =========================
def fetch_historical(security_id, segment):

    url = f"{BASE_URL}/charts/intraday"

    to_date = datetime.now()
    from_date = to_date - timedelta(days=1)

    payload = {
        "securityId": str(security_id),
        "exchangeSegment": segment,
        "instrument": "INDEX" if segment == "IDX_I" else "EQUITY",
        "interval": "5",
        "oi": False,
        "fromDate": from_date.strftime("%Y-%m-%d %H:%M:%S"),
        "toDate": to_date.strftime("%Y-%m-%d %H:%M:%S")
    }

    try:
        res = requests.post(url, headers=headers(), json=payload)
        data = res.json()

        if "data" not in data:
            return []

        d = data["data"]

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

    except:
        return []

# =========================
# 📦 EXPIRED OPTIONS
# =========================
def fetch_expired(security_id):

    url = f"{BASE_URL}/charts/rollingoption"

    payload = {
        "exchangeSegment": "NSE_FNO",
        "interval": "1",
        "securityId": security_id,
        "instrument": "OPTIDX",
        "expiryFlag": "WEEK",
        "expiryCode": 0,
        "strike": "ATM",
        "drvOptionType": "CALL",
        "requiredData": ["open", "high", "low", "close"]
    }

    try:
        res = requests.post(url, headers=headers(), json=payload)
        data = res.json()

        return data.get("data", {})

    except:
        return {}

# =========================
# 🔥 FULL DATA PACK
# =========================
def get_full_data(symbol):

    security_id, segment = get_symbol_info(symbol)

    if not security_id:
        return {"error": "Invalid Symbol"}

    # LTP
    ltp = fetch_ltp(security_id, segment)

    # Expiry
    expiries = fetch_expiry(security_id, segment)
    expiry = expiries[0] if expiries else None

    # Option Chain
    option_chain = {}
    if expiry:
        option_chain = fetch_option_chain(security_id, segment, expiry)

    # Historical
    historical = fetch_historical(security_id, segment)

    # Expired
    expired = fetch_expired(security_id)

    return {
        "symbol": symbol,
        "security_id": security_id,
        "segment": segment,
        "ltp": ltp,
        "expiry": expiry,
        "expiries": expiries,
        "option_chain": option_chain,
        "historical": historical,
        "expired": expired
    }
