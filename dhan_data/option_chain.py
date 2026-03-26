import logging

from dhan_data.client import (
    normalize_exchange_segment,
    sdk_option_chain,
    sdk_option_chain_expiry_list,
)

_logger = logging.getLogger(__name__)


def _normalize_expiry_list(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        data = payload.get("data") if "data" in payload else payload
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("expiries", "expiryList", "expiry", "items"):
                value = data.get(key)
                if isinstance(value, list):
                    return value
    return []


def get_expiry_list(security_id, segment="NSE_INDEX"):
    exchange_segment = normalize_exchange_segment(segment) or "NSE_INDEX"
    data, err = sdk_option_chain_expiry_list(security_id, exchange_segment)
    if err:
        return [], err
    expiries = sorted({str(expiry) for expiry in _normalize_expiry_list(data) if expiry})
    if not expiries:
        return [], "No expiry found"
    return expiries, None


def get_option_chain(security_id, expiry=None, segment=None, exchange_segment=None):
    underlying_segment = normalize_exchange_segment(segment or exchange_segment) or "NSE_INDEX"
    expiries, err = get_expiry_list(security_id, underlying_segment)
    if err:
        return None, err
    selected_expiry = expiry or (expiries[0] if expiries else None)
    if not selected_expiry:
        return None, "No expiry found"

    data, err = sdk_option_chain(security_id, underlying_segment, selected_expiry)
    if err:
        return None, err
    response = data if isinstance(data, dict) else {"data": data}
    if "data" not in response and isinstance(data, dict):
        response = {"data": data}
    response["expiries"] = expiries
    response["selected_expiry"] = selected_expiry
    return response, None
