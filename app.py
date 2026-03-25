import streamlit as st
import requests
import pandas as pd
import time
import pyotp
from datetime import datetime, timedelta

# =========================
# CONFIG
# =========================
BASE_URL = "https://api.dhan.co/v2"
AUTH_URL = "https://auth.dhan.co/app/generateAccessToken"

st.set_page_config(layout="wide")
st.title("🚀 Dhan Full Debug Dashboard")

# =========================
# TOKEN (AUTO FIXED)
# =========================
def get_token():

    if "token" not in st.session_state:
        totp = pyotp.TOTP(st.secrets["TOTP_SECRET"]).now()

        payload = {
            "dhanClientId": st.secrets["CLIENT_ID"],
            "pin": st.secrets["PIN"],
            "totp": totp
        }

        res = requests.post(AUTH_URL, params=payload)
        data = res.json()

        if "accessToken" in data:
            st.session_state.token = data["accessToken"]
        else:
            st.error(f"Token Error: {data}")
            return None

    return st.session_state.token


def get_headers():
    return {
        "access-token": get_token(),
        "client-id": st.secrets["CLIENT_ID"],
        "Content-Type": "application/json"
    }

# =========================
# SAFE API CALL
# =========================
_last_call = 0

def safe_post(url, payload):
    global _last_call

    wait = max(0, 1 - (time.time() - _last_call))
    if wait > 0:
        time.sleep(wait)

    try:
        res = requests.post(url, headers=get_headers(), json=payload, timeout=10)
        _last_call = time.time()

        if res.status_code != 200:
            return None, f"HTTP {res.status_code}"

        data = res.json()

        if "808" in str(data):
            return None, "Token Expired"

        return data, None

    except Exception as e:
        return None, str(e)

# =========================
# SYMBOLS
# =========================
symbols = {
    "NIFTY": (13, "IDX_I", "INDEX"),
    "RELIANCE": (2885, "NSE_EQ", "EQUITY"),
}

# =========================
# LTP
# =========================
def get_ltp(sec, seg):
    payload = {
        "instruments": [
            {"exchangeSegment": seg, "securityId": sec}
        ]
    }

    data, err = safe_post(f"{BASE_URL}/marketquote", payload)

    if err:
        return 0, err

    try:
        return data["data"][0]["lastPrice"], None
    except:
        return 0, "Parse Error"

# =========================
# DEPTH
# =========================
def get_depth(sec, seg):
    payload = {
        "instruments": [
            {"exchangeSegment": seg, "securityId": sec}
        ]
    }

    data, err = safe_post(f"{BASE_URL}/marketfeed/quote", payload)

    if err:
        return None, err

    try:
        return data["data"][0], None
    except:
        return None, "Depth Parse Error"

# =========================
# HISTORICAL
# =========================
def get_historical(sec, seg, inst):
    payload = {
        "securityId": str(sec),
        "exchangeSegment": seg,
        "instrument": inst,
        "expiryCode": 0,
        "oi": False,
        "fromDate": (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d"),
        "toDate": datetime.now().strftime("%Y-%m-%d"),
    }

    data, err = safe_post(f"{BASE_URL}/charts/historical", payload)

    if err:
        return None, err

    if not data or "open" not in data:
        return None, "No Data"

    df = pd.DataFrame({
        "open": data["open"],
        "high": data["high"],
        "low": data["low"],
        "close": data["close"],
        "volume": data["volume"],
    })

    return df, None

# =========================
# INTRADAY
# =========================
def get_intraday(sec, seg, inst):
    payload = {
        "securityId": str(sec),
        "exchangeSegment": seg,
        "instrument": inst,
        "interval": "1",
        "oi": False,
        "fromDate": datetime.now().strftime("%Y-%m-%d"),
        "toDate": datetime.now().strftime("%Y-%m-%d"),
    }

    data, err = safe_post(f"{BASE_URL}/charts/intraday", payload)

    if err:
        return None, err

    if not data or "open" not in data:
        return None, "No Candle Data"

    df = pd.DataFrame({
        "open": data["open"],
        "high": data["high"],
        "low": data["low"],
        "close": data["close"],
    })

    return df, None

# =========================
# UI
# =========================
st.subheader("📊 SYMBOLS")
for k, v in symbols.items():
    st.write(k, v)

sec, seg, inst = symbols["RELIANCE"]

# LTP
st.subheader("📈 LTP STATUS")
ltp, ltp_err = get_ltp(sec, seg)
st.success(f"LTP: {ltp}" if ltp else f"LTP Error: {ltp_err}")

# DEPTH
st.subheader("📊 DEPTH STATUS")
depth, d_err = get_depth(sec, seg)
st.success("Depth OK") if depth else st.warning(f"Depth Error: {d_err}")

# HISTORICAL
st.subheader("📅 HISTORICAL")
hist, h_err = get_historical(sec, seg, inst)
if hist is not None:
    st.dataframe(hist.tail())
else:
    st.warning(f"Historical Error: {h_err}")

# CANDLE
st.subheader("🕯 CANDLE")
candle, c_err = get_intraday(sec, seg, inst)
if candle is not None:
    st.line_chart(candle["close"])
else:
    st.warning(f"Candle Error: {c_err}")

# DEBUG
st.subheader("🛠 DEBUG PANEL")
st.write("Token:", "✅")
st.write("LTP:", ltp)
st.write("Depth:", "OK" if depth else "FAIL")
st.write("Historical:", "OK" if hist is not None else "FAIL")
st.write("Candle:", "OK" if candle is not None else "FAIL")

if st.button("🔄 Refresh"):
    st.rerun()

st.success("✅ SYSTEM RUNNING")
