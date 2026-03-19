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

        st.write("📦 RAW EXPIRY RESPONSE:", res)

        # ✅ सही parsing
        if res and res.get("status") == "success":
            return res.get("data", [])

        return []

    except Exception as e:
        st.error(f"❌ Expiry Error: {e}")
        return []
