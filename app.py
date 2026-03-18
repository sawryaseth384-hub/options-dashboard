import requests
import streamlit as st

st.title("API TEST")

headers = {
    "access-token": st.secrets["ACCESS_TOKEN"],
    "client-id": st.secrets["CLIENT_ID"],
    "Content-Type": "application/json"
}

payload = {
    "NSE_EQ": [11536]
}

res = requests.post(
    "https://api.dhan.co/v2/marketfeed/ltp",
    headers=headers,
    json=payload
)

st.write("STATUS:", res.status_code)
st.write(res.text)
