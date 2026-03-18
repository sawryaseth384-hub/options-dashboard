import streamlit as st
from core.sentiment import get_sentiment

def show_header(data):

    # 🔥 CUSTOM CSS (LOOK FIX)
    st.markdown("""
    <style>
    .market-card {
        background: #111;
        padding: 10px 14px;
        border-radius: 12px;
        text-align: center;
        border: 1px solid #222;
        transition: 0.2s;
    }
    .market-card:hover {
        background: #1a1a1a;
    }
    .name {
        font-size: 12px;
        color: #aaa;
    }
    .price {
        font-size: 16px;
        font-weight: 600;
        color: white;
    }
    .green {
        color: #00e676;
        font-size: 12px;
    }
    .red {
        color: #ff5252;
        font-size: 12px;
    }
    .section-title {
        font-size: 15px;
        font-weight: 600;
        color: #ccc;
        margin-top: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

    def card(col, name, val):
        change = val["change"]
        cls = "green" if change > 0 else "red"

        col.markdown(f"""
        <div class="market-card">
            <div class="name">{name}</div>
            <div class="price">{val['ltp']}</div>
            <div class="{cls}">{change}</div>
        </div>
        """, unsafe_allow_html=True)

    # 🔥 ROW 1 — INDIAN
    st.markdown("### 🇮🇳 Market")
    cols = st.columns(4)
    card(cols[0], "NIFTY", data["NIFTY"])
    card(cols[1], "BANKNIFTY", data["BANKNIFTY"])
    card(cols[2], "SENSEX", data["SENSEX"])
    card(cols[3], "VIX", data["VIX"])

    # 🔥 ROW 2 — GLOBAL
    st.markdown("### 🌍 Global")
    cols = st.columns(3)
    card(cols[0], "DOW", data["DOW"])
    card(cols[1], "NASDAQ", data["NASDAQ"])
    card(cols[2], "GIFT", data["GIFT"])

    # 🔥 ROW 3 — COMMODITY
    st.markdown("### 🪙 Commodity")
    cols = st.columns(3)
    card(cols[0], "CRUDE", data["CRUDE"])
    card(cols[1], "GOLD", data["GOLD"])
    card(cols[2], "SILVER", data["SILVER"])

    # 🔥 ROW 4 — CURRENCY
    st.markdown("### 💱 Currency")
    cols = st.columns(2)
    card(cols[0], "USDINR", data["USDINR"])
    card(cols[1], "DXY", data["DXY"])

    # 🔥 SENTIMENT BAR
    sentiment = get_sentiment(data)

    st.markdown(f"""
    <div style="
        background:#111;
        padding:10px;
        border-radius:10px;
        margin-top:10px;
        text-align:center;
        border:1px solid #222;
    ">
        📊 <b style="color:white">Market Sentiment:</b> 
        <span style="color:#00e676">{sentiment}</span>
    </div>
    """, unsafe_allow_html=True)

    st.divider()
