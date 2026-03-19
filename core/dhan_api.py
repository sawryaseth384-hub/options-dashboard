import os
import streamlit as st
from dhanhq import dhanhq
from datetime import datetime

# 🔥 FALLBACK DATA (important)
SAMPLE_EXPIRIES = [
    "2026-03-26",
    "2026-04-02",
    "2026-04-09",
    "2026-04-16"
]

# ✅ DHAN CLIENT
@st.cache_resource
def get_dhan_client():
    client_id = os.getenv("DHAN_CLIENT_ID")
    access_token = os.getenv("DHAN_ACCESS_TOKEN")

    if not client_id or not access_token:
        st.error("❌ API credentials missing")
        return None

    return dhanhq(client_id, access_token)


# ✅ EXPIRY LIST
@st.cache_data(ttl=60)
def get_expiry_list():
    dhan = get_dhan_client()

    if not dhan:
        return SAMPLE_EXPIRIES  # fallback

    try:
        res = dhan.expiry_list(
            under_security_id=13,
            under_exchange_segment="IDX_I"
        )

        # 🔥 DEBUG (important)
        st.write("DEBUG EXPIRY:", res)

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
        return expiries if expiries else SAMPLE_EXPIRIES

    except Exception as e:
        st.error(f"Expiry Error: {e}")
        return SAMPLE_EXPIRIES


# ✅ OPTION CHAIN
@st.cache_data(ttl=5)
def get_option_chain(expiry):
    dhan = get_dhan_client()

    if not dhan:
        return None

    try:
        return dhan.option_chain(
            under_security_id=13,
            under_exchange_segment="IDX_I",
            expiry=expiry
        )
    except Exception as e:
        st.error(f"Option Chain Error: {e}")
        return None
