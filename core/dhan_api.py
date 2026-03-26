import requests
from core.token_manager import get_headers

BASE_URL = "https://api.dhan.co/v2"


def get_option_chain():
    url = f"{BASE_URL}/optionchain"

    payload = {
        "UnderlyingScrip": 13,
        "UnderlyingSeg": "IDX_I",
        "Expiry": "2026-03-24"
    }

    res = requests.post(url, headers=get_headers(), json=payload)

    return res.json()
