import datetime as dt
import inspect
import logging

from core import token_manager

try:
    import streamlit as st
except ImportError:  # pragma: no cover - streamlit not available in some contexts
    st = None

try:
    from dhanhq import dhanhq as DhanHQ
except ImportError:  # pragma: no cover - SDK missing
    DhanHQ = None

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

_SDK_CACHE = {"client": None, "token": None, "client_id": None}

_logger = logging.getLogger(__name__)


def normalize_exchange_segment(segment):
    if not segment:
        return None
    seg = str(segment).strip().upper()
    return SEGMENT_ALIASES.get(seg, seg)


def _get_sdk_state():
    if st is None:
        return _SDK_CACHE
    try:
        return st.session_state
    except Exception:
        return _SDK_CACHE


def _cache_sdk_client(client, token, client_id):
    _SDK_CACHE.update({"client": client, "token": token, "client_id": client_id})
    state = _get_sdk_state()
    if state is _SDK_CACHE:
        return
    try:
        state["dhan_sdk_client"] = client
        state["dhan_sdk_token"] = token
        state["dhan_sdk_client_id"] = client_id
    except Exception:
        return


def _get_cached_sdk_client():
    state = _get_sdk_state()
    if state is _SDK_CACHE:
        return _SDK_CACHE.get("client"), _SDK_CACHE.get("token"), _SDK_CACHE.get("client_id")
    try:
        return (
            state.get("dhan_sdk_client"),
            state.get("dhan_sdk_token"),
            state.get("dhan_sdk_client_id"),
        )
    except Exception:
        return _SDK_CACHE.get("client"), _SDK_CACHE.get("token"), _SDK_CACHE.get("client_id")


def get_sdk_client():
    if DhanHQ is None:
        return None, "DhanHQ SDK not installed. Install with: pip install dhanhq"
    token = token_manager.get_access_token()
    client_id = token_manager.get_client_id()
    if not token or not client_id:
        _logger.warning("Missing credentials for DhanHQ SDK client.")
        return None, "Missing credentials. Set CLIENT_ID and DHAN_ACCESS_TOKEN in Streamlit secrets or environment."
    cached_client, cached_token, cached_client_id = _get_cached_sdk_client()
    if cached_client and cached_token == token and cached_client_id == client_id:
        return cached_client, None
    try:
        client = DhanHQ(client_id, token)
    except Exception as exc:
        return None, f"Failed to initialize DhanHQ SDK: {exc}"
    _cache_sdk_client(client, token, client_id)
    return client, None


def _resolve_sdk_method(client, primary, fallbacks=None):
    fallbacks = fallbacks or []
    for name in [primary] + list(fallbacks):
        method = getattr(client, name, None)
        if callable(method):
            return method, name
    return None, None


def _call_with_signature(method, **kwargs):
    try:
        signature = inspect.signature(method)
        filtered = {key: value for key, value in kwargs.items() if key in signature.parameters}
    except (TypeError, ValueError) as exc:
        name = getattr(method, "__name__", "<unknown>")
        _logger.debug("Signature inspection failed for %s: %s", name, exc)
        filtered = kwargs
    return method(**filtered)


def _extract_status_code(payload):
    if not isinstance(payload, dict):
        return None
    for container in (payload, payload.get("remarks"), payload.get("data")):
        if not isinstance(container, dict):
            continue
        for key in ("status_code", "statusCode", "httpStatus", "code", "error_code", "errorCode"):
            value = container.get(key)
            if value is None:
                continue
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
    return None


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


def _redact_params(params):
    if not isinstance(params, dict):
        return params
    safe_keys = {
        "security_id",
        "exchange_segment",
        "instrument_type",
        "from_date",
        "to_date",
        "time_frame",
        "interval",
        "securities",
        "underlying_security_id",
        "underlying_exchange_segment",
    }
    redacted = {}
    for key, value in params.items():
        key_lower = str(key).lower()
        redacted[key] = value if key_lower in safe_keys else "***"
    return redacted


def _log_api_status(context, params, error=None):
    safe_params = _redact_params(params)
    if error:
        _logger.warning("%s failed: %s | params=%s", context, error, safe_params)
    else:
        _logger.info("%s success | params=%s", context, safe_params)


def _log_validation_error(message):
    _logger.warning(message)
    return message


def _normalize_sdk_error(payload, params=None, context="DhanHQ"):
    if payload is None:
        return f"{context} error: empty response"
    if not isinstance(payload, dict):
        return None
    if payload.get("status") in ("success", "ok", "OK"):
        return None
    if "status" not in payload and not _extract_error_message(payload):
        return None
    status_code = _extract_status_code(payload)
    message = _extract_error_message(payload)
    if status_code == 401 or (message and "unauthorized" in message.lower()):
        return "Token expired or invalid"
    if status_code == 404:
        return "Endpoint not found (404). Update the DhanHQ SDK."
    if status_code == 400:
        safe_params = _redact_params(params)
        detail = message or safe_params
        _logger.warning("Invalid parameters (400) for %s: %s", context, detail)
        return f"Invalid parameters (400): {detail}"
    if message:
        return f"{context} error: {message}"
    return f"{context} error: unexpected response"


def _sdk_call(method_name, context, params, fallback_methods=None):
    client, err = get_sdk_client()
    if err:
        _log_api_status(context, params, err)
        return None, err
    method, resolved = _resolve_sdk_method(client, method_name, fallback_methods)
    if not method:
        error = f"DhanHQ SDK method missing: {method_name}"
        _log_api_status(context, params, error)
        return None, error
    try:
        payload = _call_with_signature(method, **params)
    except Exception as exc:
        error = f"{context} error: {exc}"
        _log_api_status(context, params, error)
        return None, error
    error = _normalize_sdk_error(payload, params=params, context=context)
    if error:
        _log_api_status(context, params, error)
        return None, error
    _log_api_status(context, params, None)
    return payload, None


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


def sdk_get_quote(security_id, exchange_segment):
    security_id, err = _validate_security_id(security_id)
    if err:
        return None, err
    exchange_segment, err = _validate_exchange_segment(exchange_segment)
    if err:
        return None, err
    params = {
        "security_id": security_id,
        "exchange_segment": exchange_segment,
        "securities": {exchange_segment: [security_id]},
    }
    return _sdk_call("get_quote", "Quote", params)


def sdk_option_contracts(security_id, exchange_segment):
    security_id, err = _validate_security_id(security_id)
    if err:
        return None, err
    exchange_segment, err = _validate_exchange_segment(exchange_segment)
    if err:
        return None, err
    params = {
        "security_id": security_id,
        "exchange_segment": exchange_segment,
        "underlying_security_id": security_id,
        "underlying_exchange_segment": exchange_segment,
    }
    return _sdk_call("option_contracts", "Option contracts", params)


def sdk_intraday_daily_minute_charts(security_id, exchange_segment, instrument_type, from_date, to_date, time_frame=5):
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
    params = {
        "security_id": security_id,
        "exchange_segment": exchange_segment,
        "instrument_type": instrument_type,
        "from_date": from_date,
        "to_date": to_date,
        "time_frame": time_frame,
        "interval": time_frame,
    }
    return _sdk_call("intraday_daily_minute_charts", "Intraday charts", params)


def sdk_historical_minute_charts(security_id, exchange_segment, instrument_type, from_date, to_date, time_frame=5):
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
    params = {
        "security_id": security_id,
        "exchange_segment": exchange_segment,
        "instrument_type": instrument_type,
        "from_date": from_date,
        "to_date": to_date,
        "time_frame": time_frame,
        "interval": time_frame,
    }
    return _sdk_call("historical_minute_charts", "Historical charts", params)


def sdk_get_market_depth(security_id, exchange_segment):
    security_id, err = _validate_security_id(security_id)
    if err:
        return None, err
    exchange_segment, err = _validate_exchange_segment(exchange_segment)
    if err:
        return None, err
    params = {
        "security_id": security_id,
        "exchange_segment": exchange_segment,
    }
    return _sdk_call("get_market_depth", "Market depth", params)
