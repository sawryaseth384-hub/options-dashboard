import streamlit as st
import requests

# 🔄 Auto refresh (हर 3 सेकंड)
from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=3000, key="data_refresh")

st.set_page_config(page_title="Dhan Live Dashboard")

st.title("🚀 DHAN LIVE DASHBOARD")

# 🔐 Secrets
CLIENT_ID = st.secrets["CLIENT_ID"]
ACCESS_TOKEN = st.secrets["ACCESS_TOKEN"]

st.success("✅ Connected to Dhan")

# 🔥 API CONFIG
url = "https://api.dhan.co/v2/marketfeed/quote"

headers = {
    "access-token": ACCESS_TOKEN,
    "client-id": CLIENT_ID,
    "Content-Type": "application/json"
}

payload = {
    "NSE_EQ": [11536],
    "NSE_FNO": [49081, 49082]
}

# 🔥 API CALL (हर refresh पर)
try:
    res = requests.post(url, headers=headers, json=payload)
    data = res.json()

    if data.get("status") == "success":

        output = []

        for segment, items in data["data"].items():
            for sec_id, values in items.items():

                output.append({
                    "Segment": segment,
                    "SecurityID": sec_id,
                    "Price": values.get("last_price"),
                    "OI": values.get("oi"),
                    "Volume": values.get("volume"),
                    "Buy Qty": values.get("buy_quantity"),
                    "Sell Qty": values.get("sell_quantity")
                })

        st.subheader("📊 LIVE MARKET DATA")
        st.dataframe(output)

    else:
        st.error("❌ API Error")
        st.write(data)

except Exception as e:
    st.error(f"❌ Error: {str(e)}")
