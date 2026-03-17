import requests
from utils.config import DHAN_ACCESS_TOKEN, DHAN_CLIENT_ID

def get_market_quote():

    url = "https://api.dhan.co/v2/marketfeed/quote"

    headers = {
        "access-token": DHAN_ACCESS_TOKEN,
        "client-id": DHAN_CLIENT_ID,
        "Content-Type": "application/json"
    }

    payload = {
        "NSE_FNO": [49081]   # NIFTY example
    }

    response = requests.post(url, headers=headers, json=payload)

    return response.json()
