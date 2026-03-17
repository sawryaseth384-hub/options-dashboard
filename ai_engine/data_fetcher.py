import requests

DHAN_TOKEN = "YOUR_DHAN_API_TOKEN"

def get_nifty_price():

    url = "https://api.dhan.co/v2/marketfeed/ltp"

    headers = {
        "access-token": DHAN_TOKEN,
        "Content-Type": "application/json"
    }

    payload = {
        "NSE_INDEX": ["Nifty 50"]
    }

    r = requests.post(url, json=payload, headers=headers)

    data = r.json()

    return data
