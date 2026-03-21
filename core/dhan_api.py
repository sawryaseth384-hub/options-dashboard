import streamlit as st

# =========================
# 📦 IMPORT ALL MODULES
# =========================
from dhan_data.expiry import get_expiry
from dhan_data.option_chain import get_option_chain
from dhan_data.market_quote import get_ltp
from dhan_data.historical_data import get_historical
from dhan_data.expired_options import get_expired_options
from dhan_data.instruments import get_symbol_data

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
# 🎯 SYMBOL HANDLER (AUTO)
# =========================
def get_symbol_info(symbol):

    symbol = symbol.upper()

    # INDEX FIX
    if symbol == "NIFTY":
        return 13, "IDX_I"

    if symbol == "BANKNIFTY":
        return 25, "IDX_I"

    if symbol == "FINNIFTY":
        return 27, "IDX_I"

    # STOCK (FNO)
    data = get_symbol_data(symbol)

    if data:
        return data.get("security_id"), data.get("segment")

    return None, None

# =========================
# 📅 EXPIRY
# =========================
def fetch_expiry(security_id, segment):

    data = get_expiry(headers(), security_id, segment)

    if data and data.get("status") == "success":
        return data.get("data", [])

    return []

# =========================
# 📊 OPTION CHAIN
# =========================
def fetch_option_chain(security_id, segment, expiry):

    data = get_option_chain(headers(), security_id, segment, expiry)

    if data and data.get("status") == "success":
        return data

    return {}

# =========================
# 💰 LTP
# =========================
def fetch_ltp(security_id, segment):

    try:
        return get_ltp(headers(), security_id, segment)
    except:
        return 0

# =========================
# 📈 HISTORICAL DATA
# =========================
def fetch_historical(security_id, segment):

    data = get_historical(headers(), security_id, segment)

    if data and "data" in data:
        return data["data"]

    return []

# =========================
# 📦 EXPIRED OPTIONS
# =========================
def fetch_expired(security_id, segment):

    data = get_expired_options(headers(), security_id, segment)

    if data and data.get("status") == "success":
        return data.get("data", [])

    return []

# =========================
# 🔥 FULL DATA PACK (ALL IN ONE)
# =========================
def get_full_data(symbol):

    security_id, segment = get_symbol_info(symbol)

    if not security_id:
        return {"error": "Invalid Symbol"}

    # 🔹 LTP
    ltp = fetch_ltp(security_id, segment)

    # 🔹 Expiry
    expiries = fetch_expiry(security_id, segment)

    expiry = expiries[0] if expiries else None

    # 🔹 Option Chain
    option_chain = {}
    if expiry:
        option_chain = fetch_option_chain(security_id, segment, expiry)

    # 🔹 Historical
    historical = fetch_historical(security_id, segment)

    # 🔹 Expired Options
    expired = fetch_expired(security_id, segment)

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
