import time
import requests
import streamlit as st

BASE_URL = "https://api.dhan.co/v2"

_last_call_time = 0


def get_headers():
    return {
        "access-token": st.secrets["ACCESS_TOKEN"],
        "client-id": st.secrets["CLIENT_ID"],
        "Content-Type": "application/json"
    }


def safe_post(url, payload):
    try:
        res = requests.post(
            url,
            headers=get_headers(),
            json=payload,
            timeout=10
        )

        data = res.json()

        # Token error
        if "808" in str(data):
            st.error("❌ Token Expired / Invalid")
            return None

        # Rate limit
        if "805" in str(data):
            st.warning("⚠️ Too many requests - wait")
            return None

        return data

    except Exception as e:
        st.error(f"API Error: {e}")
        return None


# =========================
# 📊 OPTION CHAIN (FIXED)
# =========================
def get_option_chain(security_id, segment, expiry):
    global _last_call_time

    now = time.time()

    # 🔥 SAFE RATE LIMIT FIX
    wait_time = max(0, 3 - (now - _last_call_time))
    if wait_time > 0:
        time.sleep(wait_time)

    _last_call_time = time.time()

    url = f"{BASE_URL}/optionchain"

    payload = {
        "UnderlyingScrip": int(security_id),
        "UnderlyingSeg": segment,
        "Expiry": expiry
    }

    data = safe_post(url, payload)

    if not data:
        return None

    if data.get("status") != "success":
        st.warning("⚠️ Option Chain Failed")
        return None

    if "data" not in data or "oc" not in data["data"]:
        st.warning("⚠️ Invalid Option Chain Data")
        return None

    return data
