import streamlit as st
from dhanhq import dhanhq
from datetime import datetime

# 🔥 CORRECT FALLBACK DATA (valid expiry)
SAMPLE_EXPIRIES = [
    "2026-03-24",
    "2026-03-30",
    "2026-04-07",
]

# ✅ DHAN CLIENT (STREAMLIT SECRETS)
@st.cache_resource
def get_dhan_client():
    try:
        client_id = st.secrets["CLIENT_ID"]
        access_token = st.secrets["ACCESS_TOKEN"]

        return dhanhq(client_id, access_token)

    except Exception as e:
        st.error("❌ Secrets not set properly (CLIENT_ID / ACCESS_TOKEN)")
        return None


# ✅ EXPIRY LIST
@st.cache_data(ttl=60)
def get_expiry_list():
    dhan = get_dhan_client()

    if not dhan:
        return SAMPLE_EXPIRIES

    try:
        res = dhan.expiry_list(
            under_security_id=13,
            under_exchange_segment="IDX_I"
        )

        # 🔍 DEBUG
        st.write("📊 EXPIRY API RESPONSE:", res)

        if not res or "data" not in res:
            return SAMPLE_EXPIRIES

        data = res["data"]
        expiries = []

        # 🔥 HANDLE ALL CASES
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and "expiry" in item:
                    expiries.append(item["expiry"])
                elif isinstance(item, str):
                    expiries.append(item)

        elif isinstance(data, dict):
            if "expiry" in data:
                expiries.append(data["expiry"])

        # ✅ FINAL RETURN
        return sorted(expiries) if expiries else SAMPLE_EXPIRIES

    except Exception as e:
        st.error(f"❌ Expiry Error: {e}")
        return SAMPLE_EXPIRIES


# ✅ OPTION CHAIN (FINAL FIXED)
@st.cache_data(ttl=5)
def get_option_chain(expiry):
    dhan = get_dhan_client()

    if not dhan:
        return None

    try:
        # 🔥 MAIN FIX: DATE FORMAT CONVERT
        expiry_api = datetime.strptime(expiry, "%Y-%m-%d").strftime("%d-%m-%Y")

        res = dhan.option_chain(
            under_security_id=13,
            under_exchange_segment="IDX_I",
            expiry=expiry_api
        )

        # 🔍 DEBUG
        st.write(f"📊 OPTION CHAIN RESPONSE ({expiry_api}):", res)

        # 🔥 ERROR HANDLE
        if res.get("status") == "failure":
            st.error(f"❌ Invalid expiry: {expiry_api}")
            return None

        return res

    except Exception as e:
        st.error(f"❌ Option Chain Error: {e}")
        return None
