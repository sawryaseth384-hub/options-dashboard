import datetime as dt
import logging
import os
import time

import pyotp
import requests
import streamlit as st

_logger = logging.getLogger(__name__)

DEFAULT_AUTH_URL = "https://auth.dhan.co/app/generateAccessToken"
MAX_TOKEN_ATTEMPTS = 3
TOKEN_VALIDITY_SECONDS = 24 * 60 * 60  # full token lifespan
TOKEN_REFRESH_BUFFER_SECONDS = 60 * 60  # refresh one hour early to avoid mid-session expiry
TOKEN_TTL_SECONDS = TOKEN_VALIDITY_SECONDS - TOKEN_REFRESH_BUFFER_SECONDS
EPOCH_MS_THRESHOLD = 10_000_000_000  # treat larger numbers as millisecond epoch
EPOCH_S_THRESHOLD = 1_000_000_000  # treat numbers above as seconds epoch
TOKEN_SESSION_KEY = "dhan_access_token"
TOKEN_EXPIRY_KEY = "dhan_access_token_expiry"

_TOKEN_LOGGED = False
_TOKEN_EXPIRY_WARNED = False
_TOKEN_CACHE = {"token": None, "expires_at": None}


def _get_secret_value(key):
    value = None
    try:
        value = st.secrets.get(key)
    except Exception:
        value = None
    if not value:
        value = os.getenv(key)
    return str(value).strip() if value else ""


def _mask_token(token):
    token = str(token or "")
    if len(token) <= 8:
        return "***"
    return f"{token[:4]}...{token[-4:]}"


def _log_token_once(token):
    global _TOKEN_LOGGED
    if _TOKEN_LOGGED:
        return
    _TOKEN_LOGGED = True
    _logger.info("Dhan access token loaded: %s", _mask_token(token))


def _extract_access_token(payload):
    if not isinstance(payload, dict):
        return None
    for key in ("accessToken", "access_token", "access-token", "token"):
        token = payload.get(key)
        if token:
            return token
    nested = payload.get("data") or payload.get("result")
    if isinstance(nested, dict):
        for key in ("accessToken", "access_token", "access-token", "token"):
            token = nested.get(key)
            if token:
                return token
    return None


def _parse_expiry(value):
    """Convert expiry values to epoch seconds.

    Numeric values above EPOCH_MS_THRESHOLD are treated as epoch milliseconds,
    above EPOCH_S_THRESHOLD as epoch seconds, and smaller values are treated as
    relative seconds (expiresIn style).
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        numeric = float(value)
        if numeric > EPOCH_MS_THRESHOLD:
            return numeric / 1000
        if numeric > EPOCH_S_THRESHOLD:
            return numeric
        return time.time() + numeric
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        if stripped.isdigit():
            return _parse_expiry(int(stripped))
        try:
            parsed = dt.datetime.fromisoformat(stripped.replace("Z", "+00:00"))
        except Exception:
            return None
        return parsed.timestamp()
    return None


def _extract_expiry(payload):
    if not isinstance(payload, dict):
        return None
    possible = (
        payload.get("expiresIn"),
        payload.get("tokenValidity"),
        payload.get("validTill"),
        payload.get("expiry"),
        payload.get("expiresAt"),
    )
    nested = payload.get("data") or payload.get("result") or {}
    if isinstance(nested, dict):
        possible += (
            nested.get("expiresIn"),
            nested.get("tokenValidity"),
            nested.get("validTill"),
            nested.get("expiry"),
            nested.get("expiresAt"),
        )
    for value in possible:
        expiry = _parse_expiry(value)
        if expiry:
            return expiry
    return None


def _get_cached_token():
    token = _TOKEN_CACHE.get("token")
    expires_at = _TOKEN_CACHE.get("expires_at")
    if token:
        return token, expires_at
    try:
        token = st.session_state.get(TOKEN_SESSION_KEY)
        expires_at = st.session_state.get(TOKEN_EXPIRY_KEY)
    except Exception:
        token = None
        expires_at = None
    return token, expires_at


def _cache_token(token, expires_at=None):
    if not token:
        return
    if not expires_at:
        expires_at = time.time() + TOKEN_TTL_SECONDS
    _TOKEN_CACHE["token"] = token
    _TOKEN_CACHE["expires_at"] = expires_at
    try:
        st.session_state[TOKEN_SESSION_KEY] = token
        st.session_state[TOKEN_EXPIRY_KEY] = expires_at
    except Exception:
        pass


def _is_expired(expires_at):
    if not expires_at:
        return True
    try:
        return time.time() >= float(expires_at)
    except Exception:
        return True


def generate_totp(secret=None):
    """Generate a TOTP code using the configured secret."""
    secret = secret or _get_secret_value("TOTP_SECRET")
    if not secret:
        _logger.warning("TOTP secret missing in secrets.")
        return None
    try:
        return pyotp.TOTP(secret).now()
    except Exception as exc:
        _logger.warning("TOTP generation failed: %s", exc)
        return None


def _login():
    client_id = _get_secret_value("CLIENT_ID")
    pin = _get_secret_value("PIN")
    totp_secret = _get_secret_value("TOTP_SECRET")
    if not client_id or not pin or not totp_secret:
        _logger.warning("Missing CLIENT_ID, PIN, or TOTP_SECRET in secrets.")
        return None, None, "Missing credentials for token generation"
    totp = generate_totp(totp_secret)
    if not totp:
        return None, None, "TOTP generation failed"
    auth_url = _get_secret_value("DHAN_AUTH_URL") or DEFAULT_AUTH_URL
    payload = {"dhanClientId": client_id, "pin": pin, "totp": totp}
    try:
        response = requests.post(auth_url, json=payload, timeout=10)
    except Exception as exc:
        return None, None, str(exc)
    if response.status_code != 200:
        return None, None, f"HTTP {response.status_code}"
    try:
        payload = response.json()
    except Exception as exc:
        return None, None, f"Invalid JSON response: {exc}"
    token = _extract_access_token(payload)
    if not token:
        return None, None, "Access token missing in response"
    expiry = _extract_expiry(payload)
    return token, expiry, None


def login_and_get_token():
    token, expiry, error = _login()
    if token:
        _cache_token(token, expiry)
        _log_token_once(token)
        return token
    _logger.warning("Token login failed: %s", error)
    return None


def get_access_token(force_refresh=False):
    global _TOKEN_EXPIRY_WARNED
    cached_token, expires_at = _get_cached_token()
    if cached_token and not expires_at and not _TOKEN_EXPIRY_WARNED:
        _TOKEN_EXPIRY_WARNED = True
        _logger.warning("Cached token missing expiry metadata; forcing refresh.")
    if cached_token and not force_refresh and not _is_expired(expires_at):
        return cached_token
    for attempt in range(1, MAX_TOKEN_ATTEMPTS + 1):
        token = login_and_get_token()
        if token:
            return token
        if attempt < MAX_TOKEN_ATTEMPTS:
            time.sleep(0.5 * attempt)
    return None


def get_token(force_refresh=False):
    """Legacy alias for get_access_token."""
    return get_access_token(force_refresh=force_refresh)


def get_client_id():
    cached = None
    try:
        cached = st.session_state.get("client_id")
    except Exception:
        cached = None
    if cached:
        return cached
    client_id = _get_secret_value("CLIENT_ID")
    if client_id:
        try:
            st.session_state.client_id = client_id
        except Exception:
            pass
        return client_id
    return None


def get_credentials():
    client_id = _get_secret_value("CLIENT_ID")
    pin = _get_secret_value("PIN")
    totp_secret = _get_secret_value("TOTP_SECRET")
    credentials = {"CLIENT_ID": client_id, "PIN": pin, "TOTP_SECRET": totp_secret}
    missing = [name for name, value in credentials.items() if not value]
    if missing:
        _logger.warning("Missing required credentials: %s", ", ".join(missing))
        return {"_error": "Missing required credentials"}
    return {
        "client_id": client_id,
        "pin": pin,
        "totp_secret": totp_secret,
    }


def clear_token():
    _TOKEN_CACHE["token"] = None
    _TOKEN_CACHE["expires_at"] = None
    try:
        if TOKEN_SESSION_KEY in st.session_state:
            del st.session_state[TOKEN_SESSION_KEY]
        if TOKEN_EXPIRY_KEY in st.session_state:
            del st.session_state[TOKEN_EXPIRY_KEY]
    except Exception:
        pass


def get_headers():
    headers = {"Content-Type": "application/json"}
    token = get_access_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
        headers["access-token"] = token  # legacy compatibility
    return headers
