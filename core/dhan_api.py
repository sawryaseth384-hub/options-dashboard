from datetime import datetime

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
        if res and res.get("status") == "success":
            for item in res["data"]:
                if isinstance(item, str):
                    # 🔥 Nifty expiry = Tuesday (weekday=1)
                    dt = datetime.strptime(item, "%Y-%m-%d")
                    if dt.weekday() == 1:   # 1 = Tuesday
                        expiries.append(item)

        return sorted(expiries)

    except Exception as e:
        st.error(f"Expiry API error: {e}")
        return []
