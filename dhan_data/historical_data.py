import requests
from core.token_manager import get_headers

BASE_URL = "https://api.dhan.co/v2"

def get_historical(security_id, segment):
    try:
        payload = {
            "securityId": str(security_id),
            "exchangeSegment": segment,
            "instrument": "EQUITY",
            "interval": "1d",
            "fromDate": "2024-01-01",
            "toDate": "2024-12-31"
        }

        res = requests.post(
            f"{BASE_URL}/charts/historical",
            headers=get_headers(),
            json=payload
        )

        data = res.json()

        return data.get("data", {})

    except:
        return {}
