import streamlit as st

def show_header():

    st.markdown("<h1 style='text-align:center;'>📊 AI OPTIONS DASHBOARD</h1>", unsafe_allow_html=True)

    def row(title, items):
        st.markdown(f"### {title}")
        cols = st.columns(len(items))

        for col, (name, value, change) in zip(cols, items):
            color = "green" if "+" in change else "red"

            col.markdown(f"""
            <div style='padding:10px;border-radius:12px;background:#f5f7fa;text-align:center'>
                <b>{name}</b><br>
                {value}<br>
                <span style='color:{color}'>{change}</span>
            </div>
            """, unsafe_allow_html=True)

    # 🇮🇳 MARKET CORE
    row("🇮🇳 Market Core", [
        ("NIFTY", "23,700", "+120"),
        ("BANKNIFTY", "55,200", "+300"),
        ("SENSEX", "78,500", "+250"),
        ("FINNIFTY", "20,100", "+80"),
        ("VIX", "18.2", "-0.5"),
    ])

    # 🌍 GLOBAL
    row("🌍 Global Trigger", [
        ("DOW", "38,000", "+200"),
        ("NASDAQ", "16,500", "-50"),
        ("GIFT NIFTY", "23,750", "+80"),
    ])

    # 🪙 COMMODITY
    row("🪙 Commodity Impact", [
        ("CRUDE", "6,500", "+30"),
        ("GOLD", "72,000", "+100"),
        ("SILVER", "85,000", "+200"),
    ])

    # 💱 CURRENCY
    row("💱 Money Flow", [
        ("USDINR", "83.10", "+0.10"),
        ("DXY", "104.2", "-0.2"),
    ])

    # 📊 SENTIMENT
    row("📊 Market Sentiment", [
        ("PCR", "1.2", "+"),
        ("OI", "CALL BUILDUP", "-"),
        ("FII", "+1200Cr", "+"),
    ])

    st.divider()
