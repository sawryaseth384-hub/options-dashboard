from dhan_data.client import safe_post

BASE_URL = "https://api.dhan.co/v2"

def get_expiry(security_id, segment="IDX_I"):
    url = f"{BASE_URL}/optionchain/expirylist"
    payload = {
        "UnderlyingScrip": int(security_id),
        "UnderlyingSeg": segment
    }
    data, err = safe_post(url, payload)
    if err or not data:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("data") or []
    return []
