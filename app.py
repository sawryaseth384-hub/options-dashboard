import streamlit as st
import requests

st.title("AI Options Trading Dashboard")

# Direct credentials
CLIENT_ID = "1106299230"
ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzczNjM1OTc4LCJpYXQiOjE3NzM1NDk1NzgsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTA2Mjk5MjMwIn0._MqX20egfoTUbczsXOouL8PTBfoa8FkASXxoY_spTMGQUTvVOkV1OfxaQUu_7E-Z5eGGXClXFi1ap44wQDEQwQ"

url = "https://api.dhan.co/v2/marketfeed/ltp"

headers = {
    "access-token": ACCESS_TOKEN,
    "client-id": CLIENT_ID,
    "Content-Type": "application/json"
}

payload = {
    "NSE_EQ": [13]   # 13 = NIFTY
}

try:
    response = requests.post(url, json=payload, headers=headers)
    data = response.json()

    st.subheader("API Response")
    st.json(data)

    if data.get("status") == "success":
        nifty_price = data["data"]["NSE_EQ"]["13"]["last_price"]
        st.metric("NIFTY LTP", nifty_price)

    else:
        st.error("API returned error")

except Exception as e:
    st.error(f"Error: {e}")
