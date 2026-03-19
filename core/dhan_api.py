import streamlit as st
from datetime import datetime

@st.cache_data(ttl=60)
def get_expiry_list():
    dhan = get_dhan_client()

    if not dhan:
        st.warning("⚠️ Dhan client not available")
        return []

    try:
        res = dhan.expiry_list(
            under_security_id=13,
            under_exchange_segment="IDX_I"
        )

        # 🔍 DEBUG (optional – बाद में हटा सकते हो)
        st.write("📦 RAW EXPIRY RESPONSE:", res)

        expiries = []

        # ✅ Safe check
        if res and isinstance(res, dict) and res.get("status") == "success":
            data = res.get("data", [])

            for item in data:
                if isinstance(item, str):
                    try:
                        dt = datetime.strptime(item, "%Y-%m-%d")

                        # 🔥 NIFTY = Tuesday expiry only
                        if dt.weekday() == 1:
                            expiries.append(item)

                    except Exception:
                        continue

        # 🔥 अगर filter से empty हो जाए → fallback
        if not expiries:
            st.warning("⚠️ No Tuesday expiry found, showing all expiries")
            expiries = res.get("data", []) if res else []

        return sorted(expiries)

    except Exception as e:
        st.error(f"❌ Expiry API error: {e}")
        return []
