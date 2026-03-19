import streamlit as st
from dhanhq import dhanhq

# 🔥 TEMP HARDCODE (test ke liye)
CLIENT_ID = "1106299230"
ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzczOTkxNDkzLCJpYXQiOjE3NzM5MDUwOTMsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTA2Mjk5MjMwIn0.ncZAsyuAXxOIfT_6O9j_51FKeTo2lL46RzaHnHgWhnfeeb5jIMP0qGxAeK3F7bEyY7FQg8yPKuHJYQ04YV3r5w"

@st.cache_resource
def get_dhan_client():
    try:
        return dhanhq(CLIENT_ID, ACCESS_TOKEN)
    except Exception as e:
        st.error(f"Client Error: {e}")
        return None


@st.cache_data(ttl=60)
def get_expiry_list():
    dhan = get_dhan_client()

    if not dhan:
        st.error("❌ Client not created")
        return []

    try:
        res = dhan.expiry_list(
            under_security_id=13,
            under_exchange_segment="IDX_I"
        )

        st.write("📦 API RESPONSE:", res)  # 👈 IMPORTANT

        expiries = []

        if res and "data" in res:
            for item in res["data"]:
                if isinstance(item, dict) and "expiry" in item:
                    expiries.append(item["expiry"])

        return expiries

    except Exception as e:
        st.error(f"Expiry Error: {e}")
        return []
