import requests
from utils.config import DHAN_ACCESS_TOKEN, DHAN_CLIENT_ID

def get_market_depth():

    url = "https://api.dhan.co/v2/marketfeed/quote"  # example

    headers = {
        "access-token": DHAN_ACCESS_TOKEN,
        "client-id": DHAN_CLIENT_ID,
        "Content-Type": "application/json"
    }

    payload = {
        "NSE_EQ": ["SBIN"]  # example stock
    }

    response = requests.post(url, headers=headers, json=payload)

    try:
        return response.json()
    except:
        return {
            "error": "Invalid JSON response",
            "raw": response.text
        }
