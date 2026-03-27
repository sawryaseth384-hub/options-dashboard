import datetime as dt
import logging
import time

import requests
from dhan_auth import get_headers, refresh_token

try:
    import streamlit as st
except ImportError:  # pragma: no cover
    st = None

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


def _marketfeed_segment(segment):
    normalized = normalize_exchange_segment(segment)
    if not normalized:
        return None
    return MARKETFEED_SEGMENT_MAP.get(normalized, normalized)


def _emit_debug_info(context, endpoint, payload, status_code, response_json):
    if st is None:
        return
    try:
        with st.expander(f"API Debug: {context}", expanded=False):
            st.write("Endpoint:", endpoint)
            st.write("Request payload:")
            st.json(payload)
            st.write("Response status code:", status_code)
            st.write("Response JSON:")
            st.json(response_json)
    except Exception:
        return


def _extract_error_message(payload):
    if not isinstance(payload, dict):
        return None
    for container in (payload, payload.get("remarks"), payload.get("data")):
        if not isinstance(container, dict):
            continue
        for key in ("errorMessage", "error_message", "message", "error", "remarks"):
            value = container.get(key)
            if value:
                return str(value)
    return None


def _log_validation_error(message):
    _logger.warning(message)
    return message


def _rate_limit():
    global _last_call
    elapsed = time.time() - _last_call
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)
    _last_call = time.time()


def _rest_call(context, endpoint, payload):
    url = f"{BASE_URL}/{endpoint.lstrip('/')}"
    attempts = 0
    tried_401 = False
    while attempts <= 2:
        _rate_limit()
        headers = get_headers()
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=20)
        except (requests.Timeout, requests.ConnectionError, requests.RequestException) as exc:
            attempts += 1
            if attempts > 2:
                error = f"{context} error: {exc}"
                _emit_debug_info(context, url, payload, None, {"error": str(exc)})
                return None, error
            time.sleep(1)
            continue

        status_code = response.status_code
        if status_code == 401 and not tried_401:
            tried_401 = True
            refresh_token(force=True)
            time.sleep(1)
            continue

        if status_code >= 500 and attempts < 2:
            attempts += 1
            time.sleep(1)
            continue

        try:
            response_json = response.json()
        except ValueError:
            response_json = {"raw": response.text}
        _emit_debug_info(context, url, payload, status_code, response_json)

        if status_code == 401:
            return None, "Token invalid or expired (401). Update credentials."
        if status_code == 404:
            return None, "Endpoint not found (404). Check the Dhan API endpoint."
        if status_code == 400:
            detail = _extract_error_message(response_json) or response_json
            return None, f"Invalid parameters (400): {detail}"
        if status_code and status_code >= 400:
            detail = _extract_error_message(response_json) or response_json
            return None, f"{context} failed (HTTP {status_code}): {detail}"

        if isinstance(response_json, dict):
            status_text = str(response_json.get("status", "")).lower()
            if status_text and status_text not in {"success", "ok"}:
                detail = _extract_error_message(response_json) or response_json
                return None, f"{context} error: {detail}"
        return response_json, None

    return None, f"{context} failed after retries"


# other validation helpers remain unchanged
