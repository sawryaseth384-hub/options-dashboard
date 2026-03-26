import inspect
import logging
import time

import requests

from core import token_manager

try:
    import streamlit as st
except ImportError:  # pragma: no cover - streamlit not available in some contexts
    st = None

try:
    from dhanhq import dhanhq as DhanHQ
except ImportError:  # pragma: no cover - SDK missing
    DhanHQ = None

BASE_URL = "https://api.dhan.co/v2"
DEFAULT_RETRIES = 3
AUTH_ERROR_MARKERS = ("Unauthorized", "Missing Dhan token")

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

_SDK_CACHE = {"client": None, "token": None, "client_id": None}


def _full_url(path):
    path = path.lstrip("/")
    return f"{BASE_URL}/{path}"


_logger = logging.getLogger(__name__)


def _auth_error(message):
    return {"_error": message}, message


def _log_response_status(method, url, status_code):
    _logger.info("API response status: %s %s -> %s", method.upper(), url, status_code)


def _has_auth_header(headers):
    return bool(headers.get("Authorization"))


class DhanApiClient:
    def __init__(self, base_url=BASE_URL, retries=DEFAULT_RETRIES, timeout=10):
        self.base_url = base_url
        self.retries = retries
        self.timeout = timeout
        self.token = token_manager.get_access_token()

    def get_headers(self, extra=None):
        token = self.token or token_manager.get_access_token()
        if token:
            self.token = token
        headers = token_manager.get_headers()
        if extra:
            headers.update(extra)
        return headers

    def refresh_token(self):
        self.token = token_manager.get_access_token(force_refresh=True)
        return self.token

    def request(self, method, url, payload=None, params=None, headers=None, timeout=None):
        resolved_url = url if url.startswith("http") else _full_url(url)
        resolved_headers = self.get_headers(headers)
        if not _has_auth_header(resolved_headers):
            refreshed = self.refresh_token()
            if refreshed:
                resolved_headers = self.get_headers(headers)
        if not _has_auth_header(resolved_headers):
            return None, "Missing Dhan token"
        json_payload = payload if method.upper() in {"POST", "PUT", "PATCH"} else None
        try:
            response = requests.request(
                method,
                resolved_url,
                headers=resolved_headers,
                json=json_payload,
                params=params,
                timeout=timeout or self.timeout
            )
        except Exception as exc:
            return None, str(exc)
        _log_response_status(method, resolved_url, response.status_code)
        if response.status_code == 401:
            refreshed = self.refresh_token()
            if not refreshed:
                return None, "Unauthorized - token refresh failed"
            resolved_headers = self.get_headers(headers)
            try:
                response = requests.request(
                    method,
                    resolved_url,
                    headers=resolved_headers,
                    json=json_payload,
                    params=params,
                    timeout=timeout or self.timeout
                )
            except Exception as exc:
                return None, str(exc)
            _log_response_status(method, resolved_url, response.status_code)
            if response.status_code == 401:
                return None, "Unauthorized - token refresh failed"
        if response.status_code != 200:
            return None, f"HTTP {response.status_code}"
        try:
            return response.json(), None
        except Exception as exc:
            return None, f"Invalid JSON response: {exc}"

    def post(self, endpoint, payload):
        return self.request(
            "POST",
            _full_url(endpoint),
            payload=payload,
            timeout=self.timeout
        )

    def get(self, endpoint, params=None):
        return self.request(
            "GET",
            _full_url(endpoint),
            params=params,
            timeout=self.timeout
        )


def _get_default_client():
    return DhanApiClient()


def safe_request(method, url, client, payload=None, params=None, headers=None, retries=None, timeout=None):
    attempts = retries if retries is not None else client.retries
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            data, error = client.request(
                method,
                url,
                payload=payload,
                params=params,
                headers=headers,
                timeout=timeout
            )
        except Exception as exc:
            data, error = None, str(exc)
        if error is None and data is not None:
            return data, None
        last_error = error or last_error
        if error and any(marker in error for marker in AUTH_ERROR_MARKERS):
            break
        if attempt < attempts:
            time.sleep(0.5 * attempt)
    _logger.warning("Request failed after %s attempts: %s", attempts, last_error)
    return {}, last_error


def safe_post(url, payload, headers=None, retries=DEFAULT_RETRIES, timeout=10):
    client = _get_default_client()
    return safe_request(
        "POST",
        url,
        client,
        payload=payload,
        headers=headers,
        retries=retries,
        timeout=timeout
    )


def safe_get(url, headers=None, params=None, retries=DEFAULT_RETRIES, timeout=5):
    client = _get_default_client()
    return safe_request(
        "GET",
        url,
        client,
        params=params,
        headers=headers,
        retries=retries,
        timeout=timeout
    )


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
        return None, "DhanHQ SDK not installed"
    token = token_manager.get_access_token()
    client_id = token_manager.get_client_id()
    if not token or not client_id:
        return None, "Unauthorized (401) - invalid token"
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
    except (TypeError, ValueError):
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


def _normalize_sdk_error(payload, params=None, context="DhanHQ"):
    if payload is None:
        return f"{context} error: empty response"
    if isinstance(payload, dict):
        if payload.get("status") in ("success", "ok", "OK"):
            return None
        if "status" not in payload and not _extract_error_message(payload):
            return None
    status_code = _extract_status_code(payload)
    message = _extract_error_message(payload)
    if status_code == 401 or (message and "unauthorized" in message.lower()):
        return "Unauthorized (401) - invalid token"
    if status_code == 404:
        return "Endpoint not found (404) - should not happen after SDK fix"
    if status_code == 400:
        _logger.warning("Invalid parameters (400) for %s: %s", context, params)
        return f"Invalid parameters (400): {params}"
    if message:
        return f"{context} error: {message}"
    return f"{context} error: unexpected response"


def _sdk_call(method_name, context, params, fallback_methods=None):
    client, err = get_sdk_client()
    if err:
        return None, err
    method, resolved = _resolve_sdk_method(client, method_name, fallback_methods)
    if not method:
        return None, f"DhanHQ SDK method missing: {method_name}"
    try:
        payload = _call_with_signature(method, **params)
    except Exception as exc:
        return None, f"{context} error: {exc}"
    error = _normalize_sdk_error(payload, params=params, context=context)
    if error:
        return None, error
    return payload, None


def sdk_get_quote(security_id, exchange_segment):
    exchange_segment = normalize_exchange_segment(exchange_segment)
    security_id = int(security_id)
    params = {
        "security_id": security_id,
        "exchange_segment": exchange_segment,
        "securities": {exchange_segment: [security_id]},
    }
    return _sdk_call("get_quote", "Quote", params, fallback_methods=["quote_data"])


def sdk_option_contracts(security_id, exchange_segment):
    exchange_segment = normalize_exchange_segment(exchange_segment)
    params = {
        "security_id": int(security_id),
        "exchange_segment": exchange_segment,
        "underlying_security_id": int(security_id),
        "underlying_exchange_segment": exchange_segment,
    }
    return _sdk_call("option_contracts", "Option contracts", params, fallback_methods=[])


def sdk_intraday_daily_minute_charts(security_id, exchange_segment, instrument_type, from_date, to_date, time_frame=5):
    exchange_segment = normalize_exchange_segment(exchange_segment)
    params = {
        "security_id": str(security_id),
        "exchange_segment": exchange_segment,
        "instrument_type": instrument_type,
        "from_date": from_date,
        "to_date": to_date,
        "time_frame": time_frame,
        "interval": time_frame,
    }
    return _sdk_call(
        "intraday_daily_minute_charts",
        "Intraday charts",
        params,
        fallback_methods=["intraday_minute_data"],
    )


def sdk_historical_minute_charts(security_id, exchange_segment, instrument_type, from_date, to_date, time_frame=5):
    exchange_segment = normalize_exchange_segment(exchange_segment)
    params = {
        "security_id": str(security_id),
        "exchange_segment": exchange_segment,
        "instrument_type": instrument_type,
        "from_date": from_date,
        "to_date": to_date,
        "time_frame": time_frame,
        "interval": time_frame,
    }
    return _sdk_call(
        "historical_minute_charts",
        "Historical charts",
        params,
        fallback_methods=["historical_daily_data"],
    )


def sdk_get_market_depth(security_id, exchange_segment):
    exchange_segment = normalize_exchange_segment(exchange_segment)
    params = {
        "security_id": int(security_id),
        "exchange_segment": exchange_segment,
    }
    return _sdk_call("get_market_depth", "Market depth", params, fallback_methods=[])
