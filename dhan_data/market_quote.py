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
        "securityId": str(security_id),
        "exchangeSegment": segment
    }

    data, err = safe_post(f"{BASE_URL}/market/quote", payload, timeout=5)
    _last_call = time.time()
    if err or not data:
        return 0

    records = data.get("data") if isinstance(data, dict) else None
    record = None
    if isinstance(records, list) and records:
        record = records[0]
    elif isinstance(records, dict):
        if any(key in records for key in ("ltp", "lastPrice", "last_price")):
            record = records
        else:
            for value in records.values():
                if isinstance(value, dict):
                    record = value
                    break
    if isinstance(record, dict):
        return record.get("ltp") or record.get("lastPrice") or record.get("last_price") or 0
    return 0
