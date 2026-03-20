import requests
import streamlit as st

BASE_URL = "https://api.dhan.co/v2"


def get_headers():
    return {
        "access-token": st.secrets["ACCESS_TOKEN"],
        "client-id": st.secrets["CLIENT_ID"],
        "Content-Type": "application/json"
    }


# =========================
# 🔥 SEGMENT MAP (IMPORTANT)
# =========================
def map_segment(segment):
    if segment == "IDX_I":
        return "NSE_FNO"   # INDEX LTP also comes via FNO
    elif segment == "D":
        return "NSE_FNO"
    else:
        return "NSE_EQ"


# =========================
# 📊 GET LTP (MAIN FUNCTION)
# =========================
def get_ltp(security_id, segment):

    try:
        url = f"{BASE_URL}/marketfeed/ltp"

        mapped_segment = map_segment(segment)

        payload = {
            mapped_segment: [security_id]
        }

        res = requests.post(url, headers=get_headers(), json=payload)
        data = res.json()

        # 🔍 DEBUG
        st.write("LTP RAW:", data)

        if data.get("status") != "success":
            return 0

        return data["data"][mapped_segment][str(security_id)]["last_price"]

    except Exception as e:
        st.error(f"LTP Error: {e}")
        return 0
