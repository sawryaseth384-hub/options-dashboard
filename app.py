import streamlit as st
import requests

# 🔄 Auto refresh (live जैसा)
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=3000)  # 3 sec refresh
except:
    pass

st.set_page_config(page_title="Dhan Dashboard")

st.title("📊 DHAN DATA DASHBOARD")

# 🔐 Secrets
CLIENT_ID = st.secrets["CLIENT_ID"]
ACCESS_TOKEN = st.secrets["ACCESS_TOKEN"]

st.success("✅ Connected to Dhan")

# 🔘 Button
fetch = st.button("Fetch Data")

# 👉 Auto fetch (optional)
if fetch:

    url = "https://api.dhan.co/v2/marketfeed/quote"

    headers = {
        "access-token": ACCESS_TOKEN,
        "client-id": CLIENT_ID,
        "Content-Type": "application/json"
    }

    # 🔥 Instruments (change later if needed)
    payload = {
        "NSE_EQ": [11536],     # Reliance
        "NSE_FNO": [49081]     # Option
    }

    try:
        res = requests.post(url, headers=headers, json=payload)
        data = res.json()

        # ✅ RAW DATA
        st.subheader("📡 RAW DATA")
        st.json(data)

        # ✅ TABLE VIEW
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

            st.subheader("📊 CLEAN TABLE VIEW")
            st.dataframe(output)

        else:
            st.error("❌ API Error")
            st.write(data)

    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
