import requests
from utils.config import DHAN_ACCESS_TOKEN, DHAN_CLIENT_ID

def get_live_market_feed():

    url = "https://api.dhan.co/v2/marketfeed/live"

    headers = {
        "access-token": DHAN_ACCESS_TOKEN,
        "client-id": str(DHAN_CLIENT_ID)
    }

    payload = {
        "securityId": ["13"],
        "exchangeSegment": "NSE_FNO"
    }

    response = requests.post(url, headers=headers, json=payload)

    return response.json()
