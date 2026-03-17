import requests
from utils.config import DHAN_ACCESS_TOKEN, DHAN_CLIENT_ID

def get_option_chain():

    url = "https://api.dhan.co/v2/optionchain"

    headers = {
        "access-token": DHAN_ACCESS_TOKEN,
        "client-id": DHAN_CLIENT_ID,
        "Content-Type": "application/json"
    }

    payload = {
        "UnderlyingScrip": 13,
        "UnderlyingSeg": "IDX_I"
    }

    try:
        return requests.post(url, headers=headers, json=payload).json()
    except Exception as e:
        return {"error": str(e)}
