import streamlit as st
from dhanhq import dhanhq

# 🔥 FALLBACK (ALWAYS WORKING)
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
    except:
        st.error("❌ CLIENT_ID / ACCESS_TOKEN missing")
        return None


# ✅ EXPIRY LIST (FINAL SAFE VERSION)
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

        st.write("📦 EXPIRY API:", res)  # debug

        expiries = []

        if res and "data" in res:
            for item in res["data"]:
                if isinstance(item, dict) and "expiry" in item:
                    expiries.append(item["expiry"])

        # 🔥 IMPORTANT: fallback if empty
        if not expiries:
            st.warning("⚠️ Using fallback expiry")
            return FALLBACK_EXPIRIES

        return sorted(expiries)

    except Exception as e:
        st.error(f"❌ Expiry Error: {e}")
        return FALLBACK_EXPIRIES


# ✅ OPTION CHAIN (NO FORMAT CHANGE)
@st.cache_data(ttl=5)
def get_option_chain(expiry):
    dhan = get_dhan_client()

    if not dhan:
        return None

    try:
        res = dhan.option_chain(
            under_security_id=13,
            under_exchange_segment="IDX_I",
            expiry=expiry
        )

        st.write("📊 OPTION RESPONSE:", res)

        if res.get("status") == "failure":
            st.error("❌ Invalid expiry")
            return None

        return res

    except Exception as e:
        st.error(f"❌ Option Chain Error: {e}")
        return None
