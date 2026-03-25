import requests
import streamlit as st
from core.token_manager import get_headers

BASE_URL = "https://api.dhan.co/v2"

# ✅ cache बढ़ाया (429 fix)
@st.cache_data(ttl=5)
def get_ltp(security_id, segment):
    try:
        if segment == "IDX_I":
            exchange = "IDX_I"
        elif segment == "NSE_FNO":
            exchange = "NSE_FNO"
        else:
            exchange = "NSE_EQ"

        payload = {
            "IDX_I": [],
            "NSE_EQ": [],
            "NSE_FNO": []
        }
        payload[exchange] = [int(security_id)]

        res = requests.post(
            f"{BASE_URL}/marketfeed/ltp",
            headers=get_headers(),
            json=payload,
            timeout=5
        )

        if res.status_code != 200:
            return 0

        data = res.json()

        ltp = (
            data.get("data", {})
            .get(exchange, {})
            .get(str(security_id), {})
            .get("last_price", 0)
        )

        return float(ltp) if ltp else 0

    except:
        return 0
