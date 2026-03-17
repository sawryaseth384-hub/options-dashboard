import requests
from utils.config import DHAN_ACCESS_TOKEN, DHAN_CLIENT_ID

def get_historical_data():

    url = "https://api.dhan.co/v2/charts/historical"

    headers = {
        "access-token": DHAN_ACCESS_TOKEN,
        "client-id": str(DHAN_CLIENT_ID)
    }

    payload = {
        "securityId": "13",
        "exchangeSegment": "NSE_FNO",
        "interval": "1",
        "fromDate": "2026-03-01",
        "toDate": "2026-03-17"
    }

    response = requests.post(url, headers=headers, json=payload)

    return response.json()
