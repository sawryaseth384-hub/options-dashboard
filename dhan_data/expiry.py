import requests
from core.token_manager import get_headers

BASE_URL = "https://api.dhan.co/v2"

def get_expiry(security_id, segment="IDX_I"):
    """Fetch expiry list for a security with given segment."""
    url = f"{BASE_URL}/optionchain/expirylist"
    payload = {
        "UnderlyingScrip": int(security_id),
        "UnderlyingSeg": segment
    }
    try:
        res = requests.post(url, headers=get_headers(), json=payload)
        data = res.json()
        # Return the list directly (handles both list and dict with 'data' key)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "data" in data:
            return data["data"]
        else:
            return []
    except Exception as e:
        print("Expiry error:", e)
        return []
