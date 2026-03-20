def render_project_status():
    import streamlit as st

    st.sidebar.markdown("## 📊 Project Status")

    # ✅ LEVEL 1
    st.sidebar.markdown("### LEVEL 1 (Basic)")
    st.sidebar.success("✅ Option Chain")
    st.sidebar.success("✅ Expiry Selection")
    st.sidebar.success("✅ Spot Price")

    # 🔥 LEVEL 2
    st.sidebar.markdown("### LEVEL 2 (Core)")
    
    if st.session_state.get("pcr_done"):
        st.sidebar.success("✅ PCR")
    else:
        st.sidebar.error("❌ PCR")

    if st.session_state.get("sr_done"):
        st.sidebar.success("✅ Support/Resistance")
    else:
        st.sidebar.error("❌ Support/Resistance")

    # 💎 LEVEL 3
    st.sidebar.markdown("### LEVEL 3 (Advanced)")
    
    if st.session_state.get("oi_change_done"):
        st.sidebar.success("✅ OI Change")
    else:
        st.sidebar.error("❌ OI Change")

    if st.session_state.get("iv_done"):
        st.sidebar.success("✅ IV")
    else:
        st.sidebar.error("❌ IV")

    # 🚀 Progress %
    total = 6
    done = sum([
        st.session_state.get("pcr_done", False),
        st.session_state.get("sr_done", False),
        st.session_state.get("oi_change_done", False),
        st.session_state.get("iv_done", False),
        True, True  # basic features
    ])

    progress = int((done / total) * 100)

    st.sidebar.markdown("---")
    st.sidebar.progress(progress)
    st.sidebar.write(f"🚀 Progress: {progress}%")
