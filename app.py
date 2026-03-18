import requests
import streamlit as st

st.title("API TEST")

headers = {
    "access-token": st.secrets["eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzczODg1OTg5LCJpYXQiOjE3NzM3OTk1ODksInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTA2Mjk5MjMwIn0.vRYxbB0OWqCIQ02J741rAoGugbSg3DV2bU1Ub-un-mAs-8QMzTFKCbnIp0RiC3AGASX4zVfmFS1nHRRYaYPmkQ"],
    "client-id": st.secrets["1106299230"],
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
