import streamlit as st
from core.sentiment import get_sentiment

def show_header(data):

    st.markdown("## ⚡ LIVE MARKET")

    def row(items):
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

    st.markdown("### 🇮🇳 Market")
    row({
        "NIFTY": data["NIFTY"],
        "BANKNIFTY": data["BANKNIFTY"],
        "SENSEX": data["SENSEX"],
        "VIX": data["VIX"]
    })

    st.markdown("### 🌍 Global")
    row({
        "DOW": data["DOW"],
        "NASDAQ": data["NASDAQ"],
        "GIFT": data["GIFT"]
    })

    st.markdown("### 🪙 Commodity")
    row({
        "CRUDE": data["CRUDE"],
        "GOLD": data["GOLD"],
        "SILVER": data["SILVER"]
    })

    st.markdown("### 💱 Currency")
    row({
        "USDINR": data["USDINR"],
        "DXY": data["DXY"]
    })

    st.markdown(f"### 📊 Sentiment: {get_sentiment(data)}")

    st.divider()
