import streamlit as st
import requests
import os

st.title("AI Options Trading Dashboard")

client_id = os.getenv("1106299230")
access_token = os.getenv("eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzczNjM1OTc4LCJpYXQiOjE3NzM1NDk1NzgsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTA2Mjk5MjMwIn0._MqX20egfoTUbczsXOouL8PTBfoa8FkASXxoY_spTMGQUTvVOkV1OfxaQUu_7E-Z5eGGXClXFi1ap44wQDEQwQ")

try:
    url = "https://api.dhan.co/v2/marketfeed/ltp"

    headers = {
        "access-token": access_token,
        "client-id": client_id,
        "Content-Type": "application/json"
    }

    payload = {
        "instruments": [
            {
                "exchangeSegment": "NSE_EQ",
                "securityId": "13"
            }
        ]
    }

    response = requests.post(url, headers=headers, json=payload)
    data = response.json()

    nifty_price = data["data"][0]["lastPrice"]

    st.metric("NIFTY LTP", nifty_price)

except Exception as e:
    st.error(e)
