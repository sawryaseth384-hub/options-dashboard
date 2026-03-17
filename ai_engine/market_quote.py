import requests
import os

def get_market_quote():
    ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN")

    url = "https://api.dhan.co/v2/marketfeed/ltp"

    headers = {
        "access-token": ACCESS_TOKEN,
        "Content-Type": "application/json"
    }

    payload = {
        "IDX_I": [13, 25]
    }

    res = requests.post(url, json=payload, headers=headers)
    return res.json()
