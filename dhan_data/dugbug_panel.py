import streamlit as st

def show_debug(token, ltp, hist, oc_ok):
    st.subheader("🛠 DEBUG PANEL")

    if token:
        st.success("✅ Token OK")
    else:
        st.error("❌ Token Fail")

    if ltp:
        st.success(f"✅ LTP OK: {ltp}")
    else:
        st.warning("⚠️ LTP Zero")

    if hist:
        st.success("✅ Historical OK")
    else:
        st.warning("⚠️ No Historical Data")

    if oc_ok:
        st.success("✅ Option Chain OK")
    else:
        st.warning("⚠️ OC Failed")
