import time

from dhan_data.client import extract_marketfeed_record, normalize_exchange_segment, sdk_get_quote

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
        return None, err or "No data returned from LTP endpoint"

    record = extract_marketfeed_record(data, segment, security_id)
    if not isinstance(record, dict):
        return None, "No LTP record found in response"

    ltp = record.get("ltp")
    if ltp is None:
        ltp = record.get("lastPrice")
    if ltp is None:
        ltp = record.get("last_price")
    if ltp is None:
        ltp = record.get("price")
    if ltp is None:
        return None, "LTP value missing in response"
    return ltp, None
