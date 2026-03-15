import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Options Research Dashboard", layout="wide")

st.title("Options Research Dashboard")

# NIFTY ticker
ticker = "^NSEI"

try:

    # Fetch NIFTY data
    nifty = yf.Ticker(ticker)

    hist = nifty.history(period="1d", interval="1m")

    price = hist["Close"].iloc[-1]

    st.metric("NIFTY 50 Price", round(price,2))

    st.subheader("Intraday Chart")

    st.line_chart(hist["Close"])

    st.subheader("Recent Data")

    st.dataframe(hist.tail(20))

except Exception as e:

    st.error("Error loading price data")
    st.write(e)

# ---------- OPTION CHAIN ----------

try:

    st.subheader("Option Chain")

    expiries = nifty.options

    if len(expiries) > 0:

        expiry = expiries[0]

        opt = nifty.option_chain(expiry)

        calls = opt.calls
        puts = opt.puts

        st.write("Expiry:", expiry)

        col1, col2 = st.columns(2)

        with col1:
            st.write("CALLS")
            st.dataframe(calls)

        with col2:
            st.write("PUTS")
            st.dataframe(puts)

    else:
        st.write("No options data")

except Exception as e:

    st.error("Option chain load error")
    st.write(e)
