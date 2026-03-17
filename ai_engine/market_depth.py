import requests
import os

def get_market_quote():
    ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN")
    CLIENT_ID = os.getenv("DHAN_CLIENT_ID")

    url = "https://api.dhan.co/v2/marketfeed/ltp"

    headers = {
        "access-token": ACCESS_TOKEN,
        "Content-Type": "application/json"
    }

    payload = {
        "dhanClientId": CLIENT_ID,   # ✅ IMPORTANT
        "IDX_I": [13, 25]
    }

    res = requests.post(url, json=payload, headers=headers)
    return res.json()
