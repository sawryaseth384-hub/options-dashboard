import requests
import os

DHAN_ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN")
DHAN_CLIENT_ID = os.getenv("DHAN_CLIENT_ID")

def get_nifty_price():

    url = "https://api.dhan.co/v2/marketfeed/ltp"

    headers = {
        "access-token": DHAN_ACCESS_TOKEN,
        "client-id": DHAN_CLIENT_ID,
        "Content-Type": "application/json"
    }

    payload = {
        "NSE_INDEX": ["Nifty 50"]
    }

    response = requests.post(url, headers=headers, json=payload)

    return response.json()
