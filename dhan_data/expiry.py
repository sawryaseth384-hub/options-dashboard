import logging

from dhan_data.client import safe_post
from dhan_data.security_map import SECURITY_MAP

BASE_URL = "https://api.dhan.co/v2"
EXPIRY_PLACEHOLDER_NEAREST = "nearest"
_logger = logging.getLogger(__name__)

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


def get_expiry_list(symbol, segment="IDX_I"):
    """Return expiry list with a placeholder string when the API is unavailable."""
    symbol = str(symbol or "").upper()
    security_id = SECURITY_MAP.get(symbol)
    if not security_id:
        return [EXPIRY_PLACEHOLDER_NEAREST]
    url = f"{BASE_URL}/optionchain/expirylist"
    payload = {
        "UnderlyingScrip": int(security_id),
        "UnderlyingSeg": segment
    }
    try:
        data, err = safe_post(url, payload, timeout=10)
    except Exception as exc:
        _logger.warning("Expiry list fallback for %s: %s", symbol, exc)
        return [EXPIRY_PLACEHOLDER_NEAREST]
    if err or not data:
        return [EXPIRY_PLACEHOLDER_NEAREST]
    if isinstance(data, list):
        return data or [EXPIRY_PLACEHOLDER_NEAREST]
    if isinstance(data, dict):
        expiries = data.get("data") or []
        return expiries or [EXPIRY_PLACEHOLDER_NEAREST]
    return [EXPIRY_PLACEHOLDER_NEAREST]
