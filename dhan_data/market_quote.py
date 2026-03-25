import requests
import time
from core.token_manager import get_headers

BASE_URL = "https://api.dhan.co/v2"
_last_call = 0

def get_ltp(security_id, segment):
    global _last_call

    # 🔥 Rate limit control
    wait = max(0, 1 - (time.time() - _last_call))
    if wait > 0:
        time.sleep(wait)

    payload = {
        "instruments": [
            {
                "exchangeSegment": segment,
                "securityId": int(security_id)
            }
        ]
    }

    try:
        res = requests.post(
            f"{BASE_URL}/marketquote",
            headers=get_headers(),
            json=payload,
            timeout=5
        )

        _last_call = time.time()

        if res.status_code != 200:
            return 0

        data = res.json()

        if "data" in data and len(data["data"]) > 0:
            return data["data"][0].get("lastPrice", 0)

        return 0

    except:
        return 0
