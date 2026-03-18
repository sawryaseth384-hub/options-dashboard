import streamlit as st
import requests

st.title("🔥 DHAN API TEST")

# ✅ सही तरीके से secrets पढ़ना
CLIENT_ID = st.secrets["CLIENT_ID"]
ACCESS_TOKEN = st.secrets["ACCESS_TOKEN"]

# ✅ headers
headers = {
    "access-token": ACCESS_TOKEN,
    "client-id": CLIENT_ID,
    "Content-Type": "application/json"
}

# ✅ payload
payload = {
    "NSE_FNO": [49081]
}

# ✅ API CALL
url = "https://api.dhan.co/v2/marketfeed/quote"

if st.button("Test API"):
    try:
        res = requests.post(url, headers=headers, json=payload)
        
        st.write("Status Code:", res.status_code)
        st.json(res.json())

    except Exception as e:
        st.error(str(e))
