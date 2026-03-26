from core.token_manager import get_headers
from dhan_data.client import safe_post

BASE_URL = "https://api.dhan.co"


def get_option_chain():
    url = f"{BASE_URL}/v2/optionchain"

    payload = {
        "UnderlyingScrip": 13,
        "UnderlyingSeg": "IDX_I",
        "Expiry": "2026-03-24"
    }

    data, err = safe_post(url, payload, headers=get_headers())
    if err:
        return {"_error": err}
    return data
