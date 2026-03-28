import datetime as dt
import logging
import time

import requests
from dhan_auth import get_headers, refresh_token


BASE_URL = "https://api.dhan.co/v2"

SEGMENT_ALIASES = {
    "D": "NSE_EQ",
    "EQ": "NSE_EQ",
    "NSE_EQ": "NSE_EQ",
    "I": "NSE_INDEX",
    "IDX_I": "NSE_INDEX",
    "NSE_INDEX": "NSE_INDEX",
    "NSE_FNO": "NFO",
    "NFO": "NFO",
    "FNO": "NFO",
}

VALID_SEGMENTS = {"NSE_EQ", "NSE_INDEX", "NFO"}
VALID_INSTRUMENT_TYPES = {"INDEX", "EQUITY", "OPTIDX", "OPTSTK", "FUTIDX", "FUTSTK"}

MARKETFEED_SEGMENT_MAP = {
    "NSE_EQ": "NSE_EQ",
    "NSE_INDEX": "NSE_INDEX",
    "NFO": "NSE_FNO",
}

OPTION_CHAIN_SEGMENT_MAP = {
    "NSE_INDEX": "IDX_I",
    "NSE_EQ": "NSE_EQ",
    "NFO": "NSE_FNO",
}

_logger = logging.getLogger(__name__)
_last_call = 0.0  # rate limit tracker


def normalize_exchange_segment(segment):
    if not segment:
        return None
    seg = str(segment).strip().upper()
    return SEGMENT_ALIASES.get(seg, seg)


def normalize_option_chain_segment(segment):
    normalized = normalize_exchange_segment(segment)
    if not normalized:
        return None
    return OPTION_CHAIN_SEGMENT_MAP.get(normalized, normalized)


def _mask_headers(h):
    masked = {}
    for k, v in (h or {}).items():
        if "token" in k.lower() and isinstance(v, str):
            masked[k] = v[:4] + "..." + v[-4:]
        else:
            masked[k] = v
    return masked


def _rest_call(context, endpoint, payload):
    url = f"{BASE_URL}/{endpoint.lstrip('/')}"
    headers = get_headers()

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
    except Exception as e:
        debug = {"context": context, "url": url, "headers": _mask_headers(headers), "payload": payload, "error": str(e)}
        print(debug)
        if st is not None:
            with st.expander(f"🔥 API Debug → {context}", expanded=False):
                st.json(debug)
        return None, f"{context} network error: {e}"

    try:
        response_json = response.json()
    except Exception:
        response_json = {"raw": response.text}

    debug = {
        "context": context,
        "url": url,
        "headers": _mask_headers(headers),
        "payload": payload,
        "status": response.status_code,
        "response": response_json,
    }
    print(debug)
    if st is not None:
        with st.expander(f"🔥 API Debug → {context}", expanded=False):
            st.json(debug)

    if response.status_code == 401:
        return None, "Token invalid or expired (401). Update credentials."

    if response.status_code >= 400:
        return None, f"{context} failed: {response_json}"

    return response_json, None


# ---------- Option chain wrappers ----------
def sdk_option_chain_expiry_list(security_id, segment):
    seg = normalize_option_chain_segment(segment)
    payload = {"UnderlyingScrip": int(security_id), "UnderlyingSeg": seg}
    return _rest_call("OptionChainExpiryList", "optionChain/expiryList", payload)


def sdk_option_chain(security_id, segment, expiry):
    seg = normalize_option_chain_segment(segment)
    payload = {"UnderlyingScrip": int(security_id), "UnderlyingSeg": seg, "Expiry": str(expiry)}
    return _rest_call("OptionChain", "optionChain", payload)


__all__ = [
    "normalize_exchange_segment",
    "normalize_option_chain_segment",
    "sdk_option_chain",
    "sdk_option_chain_expiry_list",
]
