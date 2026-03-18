import streamlit as st
from core.sentiment import get_sentiment

def show_header(data):

    def item(name, val):
        change = val["change"]
        color = "#00c853" if change > 0 else "#ff1744"
        arrow = "▲" if change > 0 else "▼"

        return f"""
        <span style='margin-right:25px; font-size:13px; color:#ddd'>
            <b style='color:white'>{name}</b> {val['ltp']}
            <span style='color:{color}'> {arrow} {change}</span>
        </span>
        """

    # 🔥 CSS (Dhan style strip)
    st.markdown("""
    <style>
    .ticker {
        background: #0d0d0d;
        padding: 8px 12px;
        border-radius: 8px;
        border: 1px solid #222;
        white-space: nowrap;
        overflow-x: auto;
    }
    </style>
    """, unsafe_allow_html=True)

    # 🔥 FULL STRIP (ALL IN ONE LINE)
    st.markdown(f"""
    <div class="ticker">
        {item("NIFTY", data["NIFTY"])}
        {item("BANKNIFTY", data["BANKNIFTY"])}
        {item("SENSEX", data["SENSEX"])}
        {item("VIX", data["VIX"])}

        {item("DOW", data["DOW"])}
        {item("NASDAQ", data["NASDAQ"])}
        {item("GIFT", data["GIFT"])}

        {item("CRUDE", data["CRUDE"])}
        {item("GOLD", data["GOLD"])}
        {item("SILVER", data["SILVER"])}

        {item("USDINR", data["USDINR"])}
        {item("DXY", data["DXY"])}
    </div>
    """, unsafe_allow_html=True)

    # 🔥 SENTIMENT (small)
    sentiment = get_sentiment(data)

    st.markdown(f"""
    <div style='font-size:13px; margin-top:5px; color:#aaa'>
        📊 Sentiment: <span style='color:#00e676'>{sentiment}</span>
    </div>
    """, unsafe_allow_html=True)

    st.divider()
