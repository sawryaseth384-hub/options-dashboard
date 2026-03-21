import requests
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
# 🔄 SEGMENT → EXCHANGE MAP
# =========================
def map_exchange(segment):
    # Index (NIFTY / BANKNIFTY)
    if segment == "IDX_I":
        return "NSE_EQ"
    # Stocks / FNO
    return "NSE_FNO"


# =========================
# 🧪 DEBUG TOGGLE
# =========================
def debug_log(label, data):
    if st.sidebar.checkbox("Show Debug Data"):
        st.write(f"{label}:", data)


# =========================
# 💰 LTP (Last Price)
# =========================
def get_ltp(security_id, segment):

    exchange = map_exchange(segment)

    payload = {
        "NSE_EQ": [],
        "NSE_FNO": []
    }

    payload[exchange].append(int(security_id))

    try:
        res = requests.post(
            f"{BASE_URL}/marketfeed/ltp",
            headers=get_headers(),
            json=payload,
            timeout=10
        )

        data = res.json()
        debug_log("LTP RAW", data)

        return data.get("data", {}).get(exchange, {}).get(str(security_id), {}).get("last_price", 0)

    except Exception as e:
        st.error(f"LTP Error: {e}")
        return 0


# =========================
# 📊 OHLC DATA
# =========================
def get_ohlc(security_id, segment):

    exchange = map_exchange(segment)

    payload = {
        "NSE_EQ": [],
        "NSE_FNO": []
    }

    payload[exchange].append(int(security_id))

    try:
        res = requests.post(
            f"{BASE_URL}/marketfeed/ohlc",
            headers=get_headers(),
            json=payload,
            timeout=10
        )

        data = res.json()
        debug_log("OHLC RAW", data)

        return data.get("data", {}).get(exchange, {}).get(str(security_id), {})

    except Exception as e:
        st.error(f"OHLC Error: {e}")
        return {}


# =========================
# 📊 FULL QUOTE (Market Depth)
# =========================
def get_quote(security_id, segment):

    exchange = map_exchange(segment)

    payload = {
        "NSE_EQ": [],
        "NSE_FNO": []
    }

    payload[exchange].append(int(security_id))

    try:
        res = requests.post(
            f"{BASE_URL}/marketfeed/quote",
            headers=get_headers(),
            json=payload,
            timeout=10
        )

        data = res.json()
        debug_log("QUOTE RAW", data)

        return data.get("data", {}).get(exchange, {}).get(str(security_id), {})

    except Exception as e:
        st.error(f"Quote Error: {e}")
        return {}
