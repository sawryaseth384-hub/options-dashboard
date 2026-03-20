import streamlit as st
from dhanhq import dhanhq
from datetime import datetime

@st.cache_resource
def get_dhan_client():
    return dhanhq(st.secrets["CLIENT_ID"], st.secrets["ACCESS_TOKEN"])

@st.cache_data(ttl=300)
def get_expiry_list(security_id=13):
    """security_id: 13 for NIFTY, 25 for BANKNIFTY"""
    dhan = get_dhan_client()
    try:
        res = dhan.expiry_list(
            under_security_id=security_id,
            under_exchange_segment="IDX_I"
        )
        if res and res.get("status") == "success":
            expiries = []
            # NIFTY -> Tuesday (1), BANKNIFTY -> Thursday (3)
            target_weekday = 1 if security_id == 13 else 3
            for dt_str in res["data"]:
                dt = datetime.strptime(dt_str, "%Y-%m-%d")
                if dt.weekday() == target_weekday:
                    expiries.append(dt_str)
            return sorted(expiries)
        return []
    except Exception as e:
        st.error(f"Expiry fetch error: {e}")
        return []

@st.cache_data(ttl=5)
def get_option_chain(security_id, expiry):
    dhan = get_dhan_client()
    try:
        res = dhan.option_chain(
            under_security_id=security_id,
            under_exchange_segment="IDX_I",
            expiry=expiry
        )
        return res
    except Exception as e:
        st.error(f"Option chain error: {e}")
        return None
