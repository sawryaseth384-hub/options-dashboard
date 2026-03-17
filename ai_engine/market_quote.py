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
        "IDX_I": [13, 25]   # ✅ Nifty + BankNifty
    }

    try:
        res = requests.post(url, headers=headers, json=payload)
        return res.json()
    except Exception as e:
        return {"error": str(e)}
