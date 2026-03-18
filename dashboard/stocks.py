import streamlit as st

def show_stocks(data):

    # ===== INDIAN MARKET =====
    st.markdown("### 🇮🇳 Indian Market")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("NIFTY", data["NIFTY"]["ltp"], data["NIFTY"]["change"])

    with col2:
        st.metric("BANKNIFTY", data["BANKNIFTY"]["ltp"], data["BANKNIFTY"]["change"])

    with col3:
        st.metric("SENSEX", data["SENSEX"]["ltp"], data["SENSEX"]["change"])

    with col4:
        st.metric("VIX", data["VIX"]["ltp"], data["VIX"]["change"])


    # ===== GLOBAL MARKET =====
    st.markdown("### 🌍 Global Market")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("DOW", data["DOW"]["ltp"], data["DOW"]["change"])

    with col2:
        st.metric("NASDAQ", data["NASDAQ"]["ltp"], data["NASDAQ"]["change"])

    with col3:
        st.metric("GIFT NIFTY", data["GIFT"]["ltp"], data["GIFT"]["change"])


    # ===== COMMODITY =====
    st.markdown("### 🪙 Commodity")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("CRUDE", data["CRUDE"]["ltp"], data["CRUDE"]["change"])

    with col2:
        st.metric("GOLD", data["GOLD"]["ltp"], data["GOLD"]["change"])

    with col3:
        st.metric("SILVER", data["SILVER"]["ltp"], data["SILVER"]["change"])


    # ===== CURRENCY =====
    st.markdown("### 💱 Currency")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("USDINR", data["USDINR"]["ltp"], data["USDINR"]["change"])

    with col2:
        st.metric("DXY", data["DXY"]["ltp"], data["DXY"]["change"])
