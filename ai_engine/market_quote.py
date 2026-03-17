import requests
from utils.config import DHAN_ACCESS_TOKEN, DHAN_CLIENT_ID

def get_market_quote():

    url = "https://api.dhan.co/v2/marketfeed/ltp"

    headers = {
        "access-token": DHAN_ACCESS_TOKEN,
        "client-id": DHAN_CLIENT_ID,
        "Content-Type": "application/json"
    }

    payload = {
        "NSE_INDEX": ["Nifty 50", "Nifty Bank"]
    }

    response = requests.post(url, headers=headers, json=payload)

    return response.json()
