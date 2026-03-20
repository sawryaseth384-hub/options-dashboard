def get_ltp(security_id, segment):
    import requests
    import streamlit as st

    url = "https://api.dhan.co/v2/marketfeed/ltp"

    # ✅ FINAL FIX (DOC BASED)
    if segment in ["IDX_I", "I"]:
        exchange = "NSE_EQ"   # ❗ MOST IMPORTANT FIX
    elif segment == "D":
        exchange = "NSE_FNO"
    else:
        exchange = "NSE_EQ"

    payload = {
        "NSE_EQ": [],
        "NSE_FNO": []
    }

    payload[exchange].append(int(security_id))

    try:
        res = requests.post(url, headers={
            "access-token": st.secrets["ACCESS_TOKEN"],
            "client-id": st.secrets["CLIENT_ID"],
            "Content-Type": "application/json"
        }, json=payload)

        data = res.json()

        st.write("LTP RAW:", data)

        return data["data"][exchange][str(security_id)]["last_price"]

    except Exception as e:
        st.error(f"LTP Error: {e}")
        return 0
