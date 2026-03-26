import logging

from dhan_data.option_chain import get_expiry_list as _get_expiry_list
from dhan_data.security_map import SECURITY_MAP
EXPIRY_PLACEHOLDER_NEAREST = "nearest"  # UI placeholder when the API expiry list is unavailable.
_logger = logging.getLogger(__name__)

def get_expiry(security_id, segment="NSE_INDEX"):
    expiries, err = _get_expiry_list(security_id, segment)
    if err:
        return []
    return expiries


def get_expiry_list(symbol, segment="NSE_INDEX"):
    """Return expiry list with a placeholder string when the API is unavailable."""
    symbol = str(symbol or "").upper()
    security_id = SECURITY_MAP.get(symbol)
    if not security_id:
        return [EXPIRY_PLACEHOLDER_NEAREST]
    expiries, err = _get_expiry_list(security_id, segment)
    if err or not expiries:
        return [EXPIRY_PLACEHOLDER_NEAREST]
    return expiries
