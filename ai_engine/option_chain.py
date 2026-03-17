import requests
from utils.config import DHAN_ACCESS_TOKEN, DHAN_CLIENT_ID

def get_option_chain():

    url = "https://api.dhan.co/v2/optionchain"

    headers = {
        "access-token": DHAN_ACCESS_TOKEN,
        "client-id": str(DHAN_CLIENT_ID),
        "Content-Type": "application/json"
    }

    payload = {
        "UnderlyingScrip": "NIFTY",
        "UnderlyingSeg": "IDX_I",
        "Expiry": "",  # blank = nearest expiry
    }

    response = requests.post(url, headers=headers, json=payload)

    return response.json()
