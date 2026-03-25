import requests
import streamlit as st
from core.token_manager import get_headers

BASE_URL = "https://api.dhan.co/v2"

# ✅ Cache for performance
@st.cache_data(ttl=2)  # 2 sec cache for near-live feel
def get_ltp(security_id, segment):
    try:
        # Exchange mapping
        segment_map = {
            "IDX_I": "IDX_I",
            "NSE_FNO": "NSE_FNO",
            "NSE_EQ": "NSE_EQ"
        }

        exchange = segment_map.get(segment, "NSE_EQ")

        payload = {exchange: [int(security_id)]}

        res = requests.post(
            f"{BASE_URL}/marketfeed/ltp",
            headers=get_headers(),
            json=payload,
            timeout=5
        )

        # ✅ Check status
        if res.status_code != 200:
            st.warning(f"LTP API failed: {res.status_code}")
            return 0

        data = res.json()

        # ✅ Safe extraction
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
