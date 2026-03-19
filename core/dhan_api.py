import streamlit as st
from dhanhq import dhanhq
from datetime import datetime

# 🔥 FALLBACK
FALLBACK_EXPIRIES = [
    "2026-03-24",
    "2026-03-31",
    "2026-04-07",
    "2026-04-14"
]

# ✅ CLIENT
@st.cache_resource
def get_dhan_client():
    try:
        return dhanhq(
            st.secrets["CLIENT_ID"],
            st.secrets["ACCESS_TOKEN"]
        )
    except Exception as e:
        st.error(f"❌ Secret Error: {e}")
        return None


# ✅ EXPIRY LIST (FINAL CORRECT)
@st.cache_data(ttl=60)
def get_expiry_list():
    dhan = get_dhan_client()

    if not dhan:
        return FALLBACK_EXPIRIES

    try:
        res = dhan.expiry_list(
            under_security_id=13,
            under_exchange_segment="IDX_I"
        )

        st.write("📦 EXPIRY RAW:", res)

        if not res or res.get("status") != "success":
            return FALLBACK_EXPIRIES

        expiries = []

        # ✅ CORRECT (array of strings)
        for exp in res["data"]:
            if isinstance(exp, str):
                expiries.append(exp)

        # 🔥 IMPORTANT: empty fallback
        if not expiries:
            return FALLBACK_EXPIRIES

        return sorted(expiries)

    except Exception as e:
        st.error(f"❌ Expiry Error: {e}")
        return FALLBACK_EXPIRIES


# ✅ OPTION CHAIN (FINAL FIX)
@st.cache_data(ttl=5)
def get_option_chain(expiry):
    dhan = get_dhan_client()

    if not dhan:
        return None

    try:
        res = dhan.option_chain(
            under_security_id=13,
            under_exchange_segment="IDX_I",
            expiry=expiry   # ✅ KEEP SAME FORMAT (YYYY-MM-DD)
        )

        st.write("📊 OPTION RAW:", res)

        if not res or res.get("status") != "success":
            st.error("❌ Option API Failed")
            return None

        return res

    except Exception as e:
        st.error(f"❌ Option Chain Error: {e}")
        return None
