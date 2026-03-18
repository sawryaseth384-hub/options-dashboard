import streamlit as st

def render_watchlist(rows):

    st.subheader("📋 Watchlist")

    for r in rows:
        color = "green" if r["Change"] >= 0 else "red"

        st.markdown(
            f"<b>{r['Symbol']}</b><br><span style='color:{color}'>₹ {r['LTP']}</span>",
            unsafe_allow_html=True
        )
        st.markdown("---")
