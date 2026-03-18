# dashboard/header.py

import streamlit as st
from core.sentiment import get_sentiment
from streamlit_autorefresh import st_autorefresh
import datetime

def show_header(data):

    st_autorefresh(interval=5000)

    st.markdown("## ⚡ LIVE MARKET")

    def show_row(items):
        cols = st.columns(len(items))

        for col, (name, val) in zip(cols, items.items()):
            change = val["change"]
            color = "green" if change > 0 else "red"

            col.markdown(f"""
            <div style='text-align:center'>
            <b>{name}</b><br>
            {val['ltp']} <span style='color:{color}'>({change})</span>
            </div>
            """, unsafe_allow_html=True)

    # 🇮🇳
    st.markdown("### 🇮🇳 Market")
    show_row({
        "NIFTY": data["NIFTY"],
        "BANKNIFTY": data["BANKNIFTY"],
        "SENSEX": data["SENSEX"],
        "VIX": data["VIX"]
    })

    # 🌍
    st.markdown("### 🌍 Global")
    show_row({
        "DOW": data["DOW"],
        "NASDAQ": data["NASDAQ"],
        "GIFT": data["GIFT"]
    })

    # 🪙
    st.markdown("### 🪙 Commodity")
    show_row({
        "CRUDE": data["CRUDE"],
        "GOLD": data["GOLD"],
        "SILVER": data["SILVER"]
    })

    # 💱
    st.markdown("### 💱 Currency")
    show_row({
        "USDINR": data["USDINR"],
        "DXY": data["DXY"]
    })

    # 📊 Sentiment
    sentiment = get_sentiment(data)
    st.markdown(f"### 📊 Sentiment: {sentiment}")

    # 🕒 Market Status
    now = datetime.datetime.now().time()

    if now.hour >= 9 and now.hour <= 15:
        st.success("🟢 Market Open")
    else:
        st.error("🔴 Market Closed")

    st.divider()
