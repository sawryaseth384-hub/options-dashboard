import time
from dhan_data.client import safe_post

BASE_URL = "https://api.dhan.co/v2"
_last_call = 0


def get_ltp(security_id, segment):
    global _last_call

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

    data, err = safe_post(f"{BASE_URL}/marketfeed/ltp", payload, timeout=5)
    _last_call = time.time()
    if err or not data:
        return 0

    records = data.get("data") if isinstance(data, dict) else None
    if isinstance(records, list) and records:
        return records[0].get("ltp") or records[0].get("lastPrice") or 0
    if isinstance(records, dict):
        for value in records.values():
            if isinstance(value, dict):
                return value.get("ltp") or value.get("lastPrice") or 0
    return 0
