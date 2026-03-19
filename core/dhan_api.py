def get_expiry_list():
    try:
        res = dhan.expiry_list(
            under_security_id=13,
            under_exchange_segment="IDX_I"
        )

        import streamlit as st
        st.write("EXPIRY API RESPONSE:", res)   # 🔥 DEBUG

        return [x["expiry"] for x in res.get("data", [])]

    except Exception as e:
        import streamlit as st
        st.error(f"Expiry Error: {e}")
        return []
