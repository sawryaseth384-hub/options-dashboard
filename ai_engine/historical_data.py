import requests
from utils.config import DHAN_ACCESS_TOKEN, DHAN_CLIENT_ID

def get_historical_data():

    url = "https://api.dhan.co/v2/charts/intraday"

    headers = {
        "access-token": DHAN_ACCESS_TOKEN,
        "client-id": DHAN_CLIENT_ID,
        "Content-Type": "application/json"
    }

    payload = {
        "securityId": "13",
        "exchangeSegment": "IDX_I",
        "instrument": "INDEX",   # ✅ FIX
        "interval": "1",
        "oi": False,
        "fromDate": "2025-03-10 09:15:00",
        "toDate": "2025-03-10 15:30:00"
    }

    try:
        return requests.post(url, headers=headers, json=payload).json()
    except Exception as e:
        return {"error": str(e)}
