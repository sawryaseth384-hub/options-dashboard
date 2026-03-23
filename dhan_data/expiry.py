import requests
from core.token_manager import get_headers

BASE_URL = "https://api.dhan.co/v2"

def get_expiry(security_id):
    url = f"{BASE_URL}/optionchain/expirylist"

    payload = {
        "UnderlyingScrip": int(security_id),
        "UnderlyingSeg": "IDX_I"
    }

    res = requests.post(url, headers=get_headers(), json=payload)

    try:
        data = res.json()
        if data.get("status") == "success":
            return data.get("data", [])
        else:
            return []
    except:
        return []
