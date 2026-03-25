import requests
import streamlit as st
from core.token_manager import get_headers

BASE_URL = "https://api.dhan.co/v2"

# ✅ cache add किया (important)
@st.cache_data(ttl=2)
def get_ltp(security_id, segment):
    try:
        # segment mapping
        if segment == "IDX_I":
            exchange = "IDX_I"
        elif segment == "NSE_FNO":
            exchange = "NSE_FNO"
        else:
            exchange = "NSE_EQ"

        payload = {
            exchange: [int(security_id)]
        }

        res = requests.post(
            f"{BASE_URL}/marketfeed/ltp",
            headers=get_headers(),
            json=payload,
            timeout=5
        )

        # अगर API fail हो जाए
        if res.status_code != 200:
            st.warning(f"LTP API Error: {res.status_code}")
            return 0

        data = res.json()

        ltp = (
            data.get("data", {})
            .get(exchange, {})
            .get(str(security_id), {})
            .get("last_price", 0)
        )

        return float(ltp) if ltp else 0

    except Exception as e:
        st.error(f"LTP Error: {e}")
        return 0
