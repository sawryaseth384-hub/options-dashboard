import requests
from core.token_manager import get_headers

BASE_URL = "https://api.dhan.co/v2"

def get_option_chain(security_id, expiry):
    url = f"{BASE_URL}/optionchain/optionchain"

    payload = {
        "UnderlyingScrip": int(security_id),
        "UnderlyingSeg": "IDX_I",
        "Expiry": expiry
    }

    res = requests.post(url, headers=get_headers(), json=payload)

    try:
        return res.json()
    except:
        return {"error": "Invalid response"}
