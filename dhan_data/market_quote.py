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
# 🔥 SEGMENT FIX
# =========================
def map_exchange(segment):
    if segment in ["IDX_I", "I"]:
        return "NSE_EQ"   # index bhi yahi
    elif segment == "D":
        return "NSE_FNO"
    else:
        return "NSE_EQ"


# =========================
# 📊 LTP API
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
            json=payload
        )

        data = res.json()
        st.write("LTP RAW:", data)

        return data["data"][exchange][str(security_id)]["last_price"]

    except Exception as e:
        st.error(f"LTP Error: {e}")
        return 0


# =========================
# 📊 OHLC API
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
            json=payload
        )

        data = res.json()
        st.write("OHLC RAW:", data)

        return data["data"][exchange][str(security_id)]

    except Exception as e:
        st.error(f"OHLC Error: {e}")
        return None


# =========================
# 📊 FULL QUOTE (DEPTH)
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
            json=payload
        )

        data = res.json()
        st.write("QUOTE RAW:", data)

        return data["data"][exchange][str(security_id)]

    except Exception as e:
        st.error(f"Quote Error: {e}")
        return None
