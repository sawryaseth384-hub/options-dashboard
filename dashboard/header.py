import streamlit as st
from streamlit_autorefresh import st_autorefresh
import random

def show_header():

    # 🔁 AUTO REFRESH (हर 5 सेकंड)
    st_autorefresh(interval=5000, key="refresh")

    st.markdown("<h4 style='text-align:center;'>⚡ LIVE MARKET</h4>", unsafe_allow_html=True)

    # ===== DUMMY LIVE DATA (later API) =====
    def tick(name, base):
        change = random.randint(-200, 200)
        value = base + change
        arrow = "▲" if change > 0 else "▼"
        color = "green" if change > 0 else "red"

        return f"<span style='margin-right:15px;'><b>{name}</b> {value} <span style='color:{color}'>{arrow}{abs(change)}</span></span>"

    # ===== ROWS =====

    st.markdown(f"""
    <div style='font-size:14px'>
    {tick("NIFTY", 23700)}
    {tick("BANKNIFTY", 55200)}
    {tick("SENSEX", 78500)}
    {tick("VIX", 18)}
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style='font-size:14px'>
    {tick("DOW", 38000)}
    {tick("NASDAQ", 16500)}
    {tick("GIFT", 23750)}
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style='font-size:14px'>
    {tick("CRUDE", 6500)}
    {tick("GOLD", 72000)}
    {tick("SILVER", 85000)}
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style='font-size:14px'>
    {tick("USDINR", 83)}
    {tick("DXY", 104)}
    </div>
    """, unsafe_allow_html=True)

    st.divider()
