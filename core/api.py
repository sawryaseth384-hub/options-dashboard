import requests
from utils.config import get_keys

def fetch_data():

    CLIENT_ID, ACCESS_TOKEN = get_keys()

    url = "https://api.dhan.co/v2/marketfeed/quote"

    headers = {
        "access-token": ACCESS_TOKEN,
        "client-id": CLIENT_ID,
        "Content-Type": "application/json"
    }

    payload = {
        "NSE_EQ": [11536],
        "NSE_FNO": [49081]
    }

    res = requests.post(url, headers=headers, json=payload)

    return res.json()
