import requests
from utils.config import CLIENT_ID, ACCESS_TOKEN

def fetch_data():

    url = "https://api.dhan.co/v2/marketfeed/quote"

    headers = {
        "access-token": ACCESS_TOKEN,
        "client-id": CLIENT_ID,
        "Content-Type": "application/json"
    }

    payload = {
        "NSE_EQ": [11536],
        "NSE_FNO": [49081, 49082]
    }

    res = requests.post(url, headers=headers, json=payload)
    return res.json()
