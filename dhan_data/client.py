import datetime as dt
import logging
import time
import requests

from dhan_auth import get_headers, refresh_token  # ✅ ONLY AUTH SYSTEM

try:
    import streamlit as st
except ImportError:
    st = None

BASE_URL = "https://api.dhan.co/v2"

# =========================
# SEGMENT CONFIG
# =========================
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
VALID_INSTRUMENTS = {"INDEX", "EQUITY", "OPTIDX", "OPTSTK", "FUTIDX", "FUTSTK"}

MARKETFEED_SEGMENT_MAP = {
    "NSE_EQ": "NSE_EQ",
    "NSE_INDEX": "NSE_INDEX",
    "NFO": "NSE_FNO",
}

OPTION_CHAIN_SEGMENT_MAP = {
    "NSE_INDEX": "IDX_I",
    "NSE_EQ": "NSE_EQ",
    "NFO": "NSE_FNO",  # ✅ FIXED
}

_logger = logging.getLogger(__name__)

# =========================
# HELPERS
# =========================
def normalize_exchange_segment(segment):
    if segment is None:
        return None
    seg = str(segment).strip().upper()
    return SEGMENT_ALIASES.get(seg, seg)


def normalize_option_chain_segment(segment):
    normalized = normalize_exchange_segment(segment)
    return OPTION_CHAIN_SEGMENT_MAP.get(normalized, normalized)


def _marketfeed_segment(segment):
    normalized = normalize_exchange_segment(segment)
    return MARKETFEED_SEGMENT_MAP.get(normalized, normalized)


def _emit_debug_info(context, endpoint, payload, status_code, response_json):
    if not st:
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
    # check top-level and common nested containers
    for container in (payload, payload.get("remarks"), payload.get("data")):
        if not isinstance(container, dict):
            continue
        for key in ("errorMessage", "error_message", "message", "error", "remarks"):
            val = container.get(key)
            if val:
                return str(val)
    return None


def _validate_security_id(security_id):
    if security_id is None or str(security_id).strip() == "":
        return None, "Invalid parameters (400): security_id is required"
    try:
        value = int(security_id)
    except (TypeError, ValueError):
        return None, "Invalid parameters (400): security_id must be an integer"
    if value < 0:
        return None, "Invalid parameters (400): security_id must be non-negative"
    return value, None


def _validate_exchange_segment(segment):
    normalized = normalize_exchange_segment(segment)
    if not normalized:
        return None, "Invalid parameters (400): exchange_segment is required"
    if normalized not in VALID_SEGMENTS:
        return None, f"Invalid parameters (400): exchange_segment must be one of {sorted(VALID_SEGMENTS)}"
    return normalized, None


def _validate_instrument(instrument):
    if instrument is None or str(instrument).strip() == "":
        return None, "Invalid parameters (400): instrument is required"
    norm = str(instrument).strip().upper()
    if norm not in VALID_INSTRUMENTS:
        return None, f"Invalid parameters (400): instrument must be one of {sorted(VALID_INSTRUMENTS)}"
    return norm, None


def _validate_expiry(expiry):
    if expiry is None:
        return None, "Invalid parameters (400): expiry is required"
    text = str(expiry).strip()
    if not text:
        return None, "Invalid parameters (400): expiry is required"
    return text, None


def _parse_datetime(value):
    if isinstance(value, dt.datetime):
        return value
    if isinstance(value, dt.date):
        return dt.datetime.combine(value, dt.time.min)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _normalize_date(value, with_time=False):
    if isinstance(value, dt.datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, dt.date):
        if with_time:
            return dt.datetime.combine(value, dt.time.min).strftime("%Y-%m-%d %H:%M:%S")
        return value.strftime("%Y-%m-%d")
    if isinstance(value, str):
        return value.strip()
    return value


def _validate_date_range(from_date, to_date, with_time=False):
    if not from_date or not to_date:
        return None, None, "Invalid parameters (400): from_date and to_date are required"
    from_value = _normalize_date(from_date, with_time=with_time)
    to_value = _normalize_date(to_date, with_time=with_time)
    from_parsed = _parse_datetime(from_value)
    to_parsed = _parse_datetime(to_value)
    if not from_parsed or not to_parsed:
        return None, None, "Invalid parameters (400): from_date/to_date must be ISO date strings"
    if from_parsed > to_parsed:
        return None, None, "Invalid parameters (400): from_date must be before to_date"
    return from_value, to_value, None


# =========================
# CORE API CALL
# =========================
def _rest_call(context, endpoint, payload):
    url = f"{BASE_URL}/{endpoint}"

    try:
        headers = get_headers()
    except Exception as e:
        return None, f"Auth error: {str(e)}"

    def _post():
        return requests.post(url, headers=headers, json=payload, timeout=20)

    response = None

    # retries on network/5xx only
    for attempt in range(3):
        try:
            response = _post()
        except requests.RequestException as exc:
            if attempt == 2:
                return None, f"{context} error: {exc}"
            time.sleep(2**attempt)  # exponential backoff: 1s, 2s
            continue
        if response.status_code >= 500:
            if attempt == 2:
                break
            time.sleep(2**attempt)
            continue
        break  # got a response that’s not retriable

    if response is None:
        return None, f"{context} error: no response"

    status = response.status_code
    try:
        data = response.json()
    except Exception:
        data = {"raw": response.text}

    _emit_debug_info(context, url, payload, status, data)

    # 🔥 AUTO TOKEN REFRESH on 401 (single retry)
    if status == 401:
        try:
            _logger.info("401 received; refreshing token and retrying once")
            refresh_token()
            headers = get_headers()
            response = requests.post(url, headers=headers, json=payload, timeout=20)
            status = response.status_code
            try:
                data = response.json()
            except Exception:
                data = {"raw": response.text}
            _emit_debug_info(context + " (post-refresh)", url, payload, status, data)
        except Exception as e:
            return None, f"Token refresh failed: {str(e)}"

    if status == 404:
        return None, "Endpoint not found (404)"

    if status == 400:
        return None, f"Bad request (400): {_extract_error_message(data)}"

    if status >= 400:
        return None, f"{context} failed ({status}): {_extract_error_message(data) or data}"

    return data, None


# =========================
# API FUNCTIONS
# =========================
def get_ltp(security_id, segment):
    security_id, err = _validate_security_id(security_id)
    if err:
        return None, err
    segment, err = _validate_exchange_segment(segment)
    if err:
        return None, err
    payload = {_marketfeed_segment(segment): [security_id]}
    return _rest_call("LTP", "marketfeed/ltp", payload)


def get_option_chain(security_id, segment, expiry):
    security_id, err = _validate_security_id(security_id)
    if err:
        return None, err
    segment, err = _validate_exchange_segment(segment)
    if err:
        return None, err
    expiry, err = _validate_expiry(expiry)
    if err:
        return None, err
    payload = {
        "UnderlyingScrip": security_id,
        "UnderlyingSeg": normalize_option_chain_segment(segment),
        "Expiry": expiry,
    }
    return _rest_call("Option Chain", "optionchain", payload)


def get_intraday(security_id, segment, instrument, from_date, to_date, interval=5):
    security_id, err = _validate_security_id(security_id)
    if err:
        return None, err
    segment, err = _validate_exchange_segment(segment)
    if err:
        return None, err
    instrument, err = _validate_instrument(instrument)
    if err:
        return None, err
    from_date, to_date, err = _validate_date_range(from_date, to_date, with_time=True)
    if err:
        return None, err
    payload = {
        "securityId": str(security_id),
        "exchangeSegment": _marketfeed_segment(segment),
        "instrument": instrument,
        "expiryCode": 0,
        "fromDate": from_date,
        "toDate": to_date,
        "interval": int(interval),
    }
    return _rest_call("Intraday", "charts/intraday", payload)


def get_historical(security_id, segment, instrument, from_date, to_date, interval=5):
    security_id, err = _validate_security_id(security_id)
    if err:
        return None, err
    segment, err = _validate_exchange_segment(segment)
    if err:
        return None, err
    instrument, err = _validate_instrument(instrument)
    if err:
        return None, err
    from_date, to_date, err = _validate_date_range(from_date, to_date, with_time=False)
    if err:
        return None, err
    payload = {
        "securityId": str(security_id),
        "exchangeSegment": _marketfeed_segment(segment),
        "instrument": instrument,
        "expiryCode": 0,
        "fromDate": from_date,
        "toDate": to_date,
        "interval": int(interval),
    }
    return _rest_call("Historical", "charts/historical", payload)


def get_market_depth(security_id, segment):
    security_id, err = _validate_security_id(security_id)
    if err:
        return None, err
    segment, err = _validate_exchange_segment(segment)
    if err:
        return None, err
    payload = {_marketfeed_segment(segment): [security_id]}
    return _rest_call("Market Depth", "marketfeed/quote", payload)
