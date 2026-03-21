def get_historical(security_id, segment):
    import requests
    from datetime import datetime, timedelta
    import streamlit as st

    url = "https://api.dhan.co/v2/charts/intraday"

    to_date = datetime.now()
    from_date = to_date - timedelta(days=3)

    payload = {
        "securityId": str(security_id),
        "exchangeSegment": "NSE_EQ" if segment == "IDX_I" else segment,
        "instrument": "INDEX",
        "interval": "5",
        "oi": False,
        "fromDate": from_date.strftime("%Y-%m-%d %H:%M:%S"),
        "toDate": to_date.strftime("%Y-%m-%d %H:%M:%S")
    }

    headers = {
        "access-token": st.secrets["ACCESS_TOKEN"],
        "client-id": st.secrets["CLIENT_ID"],
        "Content-Type": "application/json"
    }

    res = requests.post(url, headers=headers, json=payload)
    data = res.json()

    if "data" not in data:
        return []

    d = data["data"]

    if "open" not in d:
        return []

    result = []

    for i in range(len(d["timestamp"])):
        result.append({
            "time": d["timestamp"][i],
            "open": d["open"][i],
            "high": d["high"][i],
            "low": d["low"][i],
            "close": d["close"][i]
        })

    return result
