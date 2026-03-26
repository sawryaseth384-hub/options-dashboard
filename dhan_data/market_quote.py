import time

from dhan_data.client import normalize_exchange_segment, sdk_get_quote

_last_call = 0


def get_ltp(security_id, segment):
    global _last_call

    wait = max(0, 1 - (time.time() - _last_call))
    if wait > 0:
        time.sleep(wait)
    _last_call = time.time()

    segment = normalize_exchange_segment(segment)
    data, err = sdk_get_quote(security_id, segment)
    if err or not data:
        return 0

    payload = data.get("data") if isinstance(data, dict) else data
    if isinstance(payload, dict) and "data" in payload:
        payload = payload.get("data")
    if isinstance(payload, list) and payload:
        payload = payload[0]
    if isinstance(payload, dict):
        return payload.get("ltp") or payload.get("lastPrice") or payload.get("last_price") or 0
    return 0
