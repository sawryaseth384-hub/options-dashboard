import streamlit as st
from dhanhq import dhanhq
from datetime import datetime, timedelta

# 🔥 CLIENT
@st.cache_resource
def get_dhan_client():
    try:
        client_id = st.secrets["CLIENT_ID"]
        access_token = st.secrets["ACCESS_TOKEN"]
        return dhanhq(client_id, access_token)
    except:
        st.error("❌ CLIENT_ID / ACCESS_TOKEN missing")
        return None


# 🔥 EXPIRY LIST
@st.cache_data(ttl=60)
def get_expiry_list():
    dhan = get_dhan_client()

    if not dhan:
        return []

    try:
        res = dhan.expiry_list(
            under_security_id=13,
            under_exchange_segment="IDX_I"
        )

        expiries = []

        if res and "data" in res:
            for item in res["data"]:
                if isinstance(item, dict) and "expiry" in item:
                    exp = item["expiry"]

                    # 🔥 FILTER (Tue + Thu)
                    dt = datetime.strptime(exp, "%Y-%m-%d")
                    if dt.weekday() in [1, 3]:
                        expiries.append(exp)

        return sorted(expiries)

    except Exception as e:
        st.error(f"❌ Expiry Error: {e}")
        return []


# 🔥 OPTION CHAIN (AUTO FIX SYSTEM)
@st.cache_data(ttl=5)
def get_option_chain(expiry):
    dhan = get_dhan_client()

    if not dhan:
        return None

    try:
        # ✅ TRY ORIGINAL
        res = dhan.option_chain(
            under_security_id=13,
            under_exchange_segment="IDX_I",
            expiry=expiry
        )

        if res.get("status") == "success":
            return res

        # 🔥 TRY THURSDAY AUTO
        dt = datetime.strptime(expiry, "%Y-%m-%d")
        thursday = dt + timedelta((3 - dt.weekday()) % 7)
        expiry_thu = thursday.strftime("%Y-%m-%d")

        res2 = dhan.option_chain(
            under_security_id=13,
            under_exchange_segment="IDX_I",
            expiry=expiry_thu
        )

        if res2.get("status") == "success":
            return res2

        st.error("❌ Invalid Expiry (Both failed)")
        return None

    except Exception as e:
        st.error(f"❌ Option Chain Error: {e}")
        return None
