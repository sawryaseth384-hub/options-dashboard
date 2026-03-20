import requests
import streamlit as st
import time

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
# ⚡ SAFE REQUEST
# =========================
def safe_post(url, payload, retry=2):
    for attempt in range(retry):
        try:
            res = requests.post(
                url,
                headers=get_headers(),
                json=payload,
                timeout=10
            )

            data = res.json()

            # 🔥 DEBUG PRINT
            print("API URL:", url)
            print("PAYLOAD:", payload)
            print("RESPONSE:", data)

            # 🔴 TOKEN ERROR
            if "808" in str(data):
                st.error("❌ Token Expired / Invalid")
                return None

            # 🔴 INVALID SECURITY
            if "813" in str(data):
                st.error("❌ Invalid Security ID")
                return None

            return data

        except Exception as e:
            if attempt < retry - 1:
                time.sleep(1)
            else:
                st.error(f"API Error: {e}")
                return None


# =========================
# 📅 EXPIRY LIST
# =========================
def get_expiry_list(security_id, segment):
    url = f"{BASE_URL}/optionchain/expirylist"

    payload = {
        "UnderlyingScrip": int(security_id),
        "UnderlyingSeg": segment
    }

    data = safe_post(url, payload)

    if not data:
        return []

    if data.get("status") != "success":
        st.warning("⚠️ Expiry Fetch Failed")
        return []

    return data.get("data", [])


def get_valid_expiries(security_id, segment):
    return get_expiry_list(security_id, segment)


# =========================
# 📊 OPTION CHAIN (RATE SAFE)
# =========================
_last_call_time = 0


def get_option_chain(security_id, segment, expiry):
    global _last_call_time

    # 🔥 RATE LIMIT HANDLE (NO SKIP, ONLY WAIT)
    now = time.time()
    if now - _last_call_time < 3:
        time.sleep(3 - (now - _last_call_time))

    _last_call_time = time.time()

    url = f"{BASE_URL}/optionchain"

    payload = {
        "UnderlyingScrip": int(security_id),
        "UnderlyingSeg": segment,
        "Expiry": expiry
    }

    data = safe_post(url, payload)

    # 🔥 DEBUG OUTPUT UI + TERMINAL
    print("OPTION CHAIN FINAL:", data)
    st.write("📊 Option Chain Debug:", data)

    if not data:
        return None

    if data.get("status") != "success":
        st.warning("⚠️ Option Chain Failed")
        return None

    # 🔥 STRUCTURE CHECK
    if "data" not in data or "oc" not in data["data"]:
        st.warning("⚠️ Invalid Option Chain Data")
        return None

    return data
