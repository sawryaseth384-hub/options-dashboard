import datetime as dt
import logging

import requests

from core import token_manager

try:
    import streamlit as st
except ImportError:  # pragma: no cover - streamlit not available in some contexts
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
    "NFO": "IDX_I",
}

_logger = logging.getLogger(__name__)


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


def _get_headers():
    token = token_manager.get_access_token()
    if not token:
        return None, "Missing access token. Set DHAN_ACCESS_TOKEN in Streamlit secrets or environment variables."
    headers = {
        "access-token": token,
        "Content-Type": "application/json",
    }
    return headers, None


def _rest_call(context, endpoint, payload):
    headers, err = _get_headers()
    url = f"{BASE_URL}/{endpoint.lstrip('/')}"
    if err:
        _emit_debug_info(context, url, payload, None, {"error": err})
        return None, err
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
    except requests.Timeout:
        error = f"{context} error: request timeout after 20 seconds"
        _emit_debug_info(context, url, payload, None, {"error": error})
        return None, error
    except requests.RequestException as exc:
        error = f"{context} error: {exc}"
        _emit_debug_info(context, url, payload, None, {"error": str(exc)})
        return None, error
    status_code = response.status_code
    try:
        response_json = response.json()
    except ValueError:
        response_json = {"raw": response.text}
    _emit_debug_info(context, url, payload, status_code, response_json)

    if status_code == 401:
        return None, "Token invalid or expired (401). Update DHAN_ACCESS_TOKEN."
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


def _validate_security_id(security_id):
    if security_id is None or security_id == "":
        return None, _log_validation_error("Invalid parameters (400): security_id is required")
    try:
        return int(security_id), None
    except (TypeError, ValueError):
        return None, _log_validation_error("Invalid parameters (400): security_id must be an integer")


def _validate_exchange_segment(exchange_segment):
    normalized = normalize_exchange_segment(exchange_segment)
    if not normalized:
        return None, _log_validation_error("Invalid parameters (400): exchange_segment is required")
    if normalized not in VALID_SEGMENTS:
        return None, _log_validation_error(
            f"Invalid parameters (400): exchange_segment must be one of {sorted(VALID_SEGMENTS)}"
        )
    return normalized, None


def _validate_instrument_type(instrument_type):
    if not instrument_type:
        return None, _log_validation_error("Invalid parameters (400): instrument_type is required")
    normalized = str(instrument_type).strip().upper()
    if normalized not in VALID_INSTRUMENT_TYPES:
        return None, _log_validation_error(
            f"Invalid parameters (400): instrument_type must be one of {sorted(VALID_INSTRUMENT_TYPES)}"
        )
    return normalized, None


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
        return None, None, _log_validation_error(
            "Invalid parameters (400): from_date and to_date are required"
        )
    from_value = _normalize_date(from_date, with_time=with_time)
    to_value = _normalize_date(to_date, with_time=with_time)
    from_parsed = _parse_datetime(from_value)
    to_parsed = _parse_datetime(to_value)
    if not from_parsed or not to_parsed:
        return None, None, _log_validation_error(
            "Invalid parameters (400): from_date/to_date must be ISO date strings"
        )
    if from_parsed > to_parsed:
        return None, None, _log_validation_error(
            "Invalid parameters (400): from_date must be before to_date"
        )
    return from_value, to_value, None


def _validate_time_frame(time_frame):
    if time_frame is None or time_frame == "":
        return None, _log_validation_error("Invalid parameters (400): time_frame is required")
    try:
        value = int(time_frame)
    except (TypeError, ValueError):
        return None, _log_validation_error("Invalid parameters (400): time_frame must be an integer")
    if value <= 0:
        return None, _log_validation_error("Invalid parameters (400): time_frame must be positive")
    return value, None


def _validate_expiry_code(expiry_code):
    """Use expiryCode=0 for cash instruments; derivatives use codes from Dhan's scrip master CSV (https://images.dhan.co/api-data/api-scrip-master.csv)."""
    if expiry_code in (None, ""):
        return 0, None
    try:
        value = int(expiry_code)
    except (TypeError, ValueError):
        return None, _log_validation_error("Invalid parameters (400): expiry_code must be an integer")
    if value < 0:
        return None, _log_validation_error("Invalid parameters (400): expiry_code must be non-negative")
    return value, None


def extract_marketfeed_record(payload, exchange_segment, security_id):
    if not isinstance(payload, dict):
        return None
    data = payload.get("data") if "data" in payload else payload
    if not isinstance(data, dict):
        return None
    segment_key = _marketfeed_segment(exchange_segment)
    segment_data = data.get(segment_key) if segment_key else None
    if segment_data is None:
        for value in data.values():
            if isinstance(value, dict) and str(security_id) in value:
                segment_data = value
                break
    if not isinstance(segment_data, dict):
        return None
    return segment_data.get(str(security_id)) or segment_data.get(int(security_id))


def _extract_depth_levels(record, depth, keys):
    for key in keys:
        value = record.get(key)
        if value is not None:
            return value
    for key in keys:
        value = depth.get(key)
        if value is not None:
            return value
    return []


def sdk_get_quote(security_id, exchange_segment):
    security_id, err = _validate_security_id(security_id)
    if err:
        return None, err
    exchange_segment, err = _validate_exchange_segment(exchange_segment)
    if err:
        return None, err
    segment_key = _marketfeed_segment(exchange_segment)
    if not segment_key:
        return None, "Invalid parameters (400): exchange_segment is required"
    params = {
        segment_key: [security_id],
    }
    return _rest_call("Live price (LTP)", "marketfeed/ltp", params)


def sdk_option_chain_expiry_list(security_id, exchange_segment):
    security_id, err = _validate_security_id(security_id)
    if err:
        return None, err
    segment = normalize_option_chain_segment(exchange_segment)
    if not segment:
        return None, "Invalid parameters (400): exchange_segment is required"
    params = {
        "UnderlyingScrip": security_id,
        "UnderlyingSeg": segment,
    }
    return _rest_call("Option chain expiry list", "optionchain/expirylist", params)


def sdk_option_chain(security_id, exchange_segment, expiry):
    security_id, err = _validate_security_id(security_id)
    if err:
        return None, err
    segment = normalize_option_chain_segment(exchange_segment)
    if not segment:
        return None, "Invalid parameters (400): exchange_segment is required"
    if expiry is None:
        return None, "Invalid parameters (400): expiry is required"
    expiry = str(expiry).strip()
    if not expiry:
        return None, "Invalid parameters (400): expiry is required"
    params = {
        "UnderlyingScrip": security_id,
        "UnderlyingSeg": segment,
        "Expiry": expiry,
    }
    return _rest_call("Option chain", "optionchain", params)


def sdk_intraday_daily_minute_charts(
    security_id,
    exchange_segment,
    instrument_type,
    from_date,
    to_date,
    time_frame=5,
    expiry_code=None,
):
    security_id, err = _validate_security_id(security_id)
    if err:
        return None, err
    exchange_segment, err = _validate_exchange_segment(exchange_segment)
    if err:
        return None, err
    instrument_type, err = _validate_instrument_type(instrument_type)
    if err:
        return None, err
    from_date, to_date, err = _validate_date_range(from_date, to_date, with_time=True)
    if err:
        return None, err
    time_frame, err = _validate_time_frame(time_frame)
    if err:
        return None, err
    expiry_code, err = _validate_expiry_code(expiry_code)
    if err:
        return None, err
    segment_key = _marketfeed_segment(exchange_segment)
    params = {
        "securityId": str(security_id),
        "exchangeSegment": segment_key,
        "instrument": instrument_type,
        "expiryCode": expiry_code,
        "oi": False,
        "fromDate": from_date,
        "toDate": to_date,
        "interval": time_frame,
    }
    return _rest_call("Intraday charts", "charts/intraday", params)


def sdk_historical_minute_charts(
    security_id,
    exchange_segment,
    instrument_type,
    from_date,
    to_date,
    time_frame=5,
    expiry_code=None,
):
    security_id, err = _validate_security_id(security_id)
    if err:
        return None, err
    exchange_segment, err = _validate_exchange_segment(exchange_segment)
    if err:
        return None, err
    instrument_type, err = _validate_instrument_type(instrument_type)
    if err:
        return None, err
    from_date, to_date, err = _validate_date_range(from_date, to_date, with_time=False)
    if err:
        return None, err
    time_frame, err = _validate_time_frame(time_frame)
    if err:
        return None, err
    expiry_code, err = _validate_expiry_code(expiry_code)
    if err:
        return None, err
    segment_key = _marketfeed_segment(exchange_segment)
    params = {
        "securityId": str(security_id),
        "exchangeSegment": segment_key,
        "instrument": instrument_type,
        "expiryCode": expiry_code,
        "oi": False,
        "fromDate": from_date,
        "toDate": to_date,
        "interval": time_frame,
    }
    return _rest_call("Historical charts", "charts/historical", params)


def sdk_get_market_depth(security_id, exchange_segment):
    security_id, err = _validate_security_id(security_id)
    if err:
        return None, err
    exchange_segment, err = _validate_exchange_segment(exchange_segment)
    if err:
        return None, err
    segment_key = _marketfeed_segment(exchange_segment)
    params = {
        segment_key: [security_id],
    }
    data, err = _rest_call("Market depth", "marketfeed/quote", params)
    if err:
        return None, err
    record = extract_marketfeed_record(data, exchange_segment, security_id)
    if not isinstance(record, dict):
        return data, None
    depth = record.get("depth") if isinstance(record.get("depth"), dict) else {}
    bids = _extract_depth_levels(record, depth, ["bids", "buy"])
    asks = _extract_depth_levels(record, depth, ["asks", "sell"])
    return {"bids": bids, "asks": asks, "record": record}, None
