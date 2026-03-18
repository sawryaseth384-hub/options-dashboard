import streamlit as st
from core.sentiment import get_sentiment

def show_header(data):

    def format_item(name, val):
        change = val["change"]
        color = "#00c853" if change > 0 else "#ff1744"

        return f"""
        <span style='margin-right:20px; font-size:14px'>
        <b>{name}</b> {val['ltp']} 
        <span style='color:{color}'>({change})</span>
        </span>
        """

    # 🔥 LINE 1 — INDIAN MARKET
    st.markdown("### 🇮🇳 Market")
    st.markdown(
        format_item("NIFTY", data["NIFTY"]) +
        format_item("BANKNIFTY", data["BANKNIFTY"]) +
        format_item("SENSEX", data["SENSEX"]) +
        format_item("VIX", data["VIX"]),
        unsafe_allow_html=True
    )

    # 🔥 LINE 2 — GLOBAL
    st.markdown("### 🌍 Global")
    st.markdown(
        format_item("DOW", data["DOW"]) +
        format_item("NASDAQ", data["NASDAQ"]) +
        format_item("GIFT", data["GIFT"]),
        unsafe_allow_html=True
    )

    # 🔥 LINE 3 — COMMODITY
    st.markdown("### 🪙 Commodity")
    st.markdown(
        format_item("CRUDE", data["CRUDE"]) +
        format_item("GOLD", data["GOLD"]) +
        format_item("SILVER", data["SILVER"]),
        unsafe_allow_html=True
    )

    # 🔥 LINE 4 — CURRENCY
    st.markdown("### 💱 Currency")
    st.markdown(
        format_item("USDINR", data["USDINR"]) +
        format_item("DXY", data["DXY"]),
        unsafe_allow_html=True
    )

    # 🔥 SENTIMENT
    st.markdown(
        f"📊 <b>Sentiment:</b> {get_sentiment(data)}",
        unsafe_allow_html=True
    )

    st.divider()
