import logging
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

import pyotp
import requests

try:
    import streamlit as st  # noqa: WPS433
except Exception:  # pragma: no cover
    st = None

from utils.secrets import get_secret  # type: ignore

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
AUTH_URL = "https://auth.dhan.co/app/generateAccessToken"
HTTP_TIMEOUT = 10
TOTP_INTERVAL = 30
REFRESH_BUFFER = timedelta(minutes=3)

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# -----------------------------------------------------------------------------
# In‑memory state
# -----------------------------------------------------------------------------
_state: Dict[str, Any] = {
    "token": None,       # str
    "expiry": None,      # datetime (UTC)
}

_lock = threading.Lock()

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _get_secret_value(key: str) -> str:
    if st is not None:
        try:
            val = st.secrets.get(key)
            if val:
                return str(val).strip()
        except Exception:
            pass
    env_val = os.getenv(key, "")
    if env_val:
        return str(env_val).strip()
    try:
        from utils.secrets import get_secret as _gs  # type: ignore
        val = _gs(key)
        if val:
            return str(val).strip()
    except Exception:
        pass
    return ""


def _load_credentials() -> Tuple[str, str, str]:
    client_id = _get_secret_value("CLIENT_ID")
    pin = _get_secret_value("DHAN_PIN")
    totp_secret = _get_secret_value("TOTP_SECRET")
    missing = [k for k, v in [("CLIENT_ID", client_id), ("DHAN_PIN", pin), ("TOTP_SECRET", totp_secret)] if not v]
    if missing:
        raise ValueError(f"Missing credentials: {', '.join(missing)}")
    return client_id, pin, totp_secret


def _generate_totp(totp_secret: str) -> str:
    totp = pyotp.TOTP(totp_secret, interval=TOTP_INTERVAL, digits=6)
    otp = totp.now()
    if len(otp) != 6:
        raise ValueError("Generated TOTP is not 6 digits")
    return otp


def _parse_expiry(expiry_raw: Any) -> datetime:
    # Supports ms epoch (int/str) or ISO8601 string
    if expiry_raw is None:
        raise ValueError("expiryTime missing in response")
    try:
        # numeric milliseconds
        ms = int(float(expiry_raw))
        return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)
    except Exception:
        pass
    try:
        dt_obj = datetime.fromisoformat(str(expiry_raw))
        if dt_obj.tzinfo is None:
            dt_obj = dt_obj.replace(tzinfo=timezone.utc)
        return dt_obj.astimezone(timezone.utc)
    except Exception:
        raise ValueError("Unable to parse expiryTime")


def _request_new_token() -> Tuple[str, datetime]:
    client_id, pin, totp_secret = _load_credentials()
    otp = _generate_totp(totp_secret)
    params = {"dhanClientId": client_id, "pin": pin, "totp": otp}
    resp = requests.post(AUTH_URL, params=params, timeout=HTTP_TIMEOUT)
    if resp.status_code == 401:
        raise PermissionError("Invalid PIN/TOTP (401)")
    if not resp.ok:
        raise RuntimeError(f"Auth error {resp.status_code}: {resp.text}")
    data = resp.json()
    token = data.get("accessToken")
    expiry_raw = data.get("expiryTime")
    if not token:
        raise RuntimeError("accessToken missing in response")
    expiry_dt = _parse_expiry(expiry_raw)
    return token, expiry_dt


def _cache_token(token: str, expiry: datetime) -> None:
    _state["token"] = token
    _state["expiry"] = expiry


def _is_expired(expiry: Optional[datetime]) -> bool:
    if not expiry:
        return True
    return _now_utc() >= (expiry - REFRESH_BUFFER)

# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------
def generate_token() -> str:
    with _lock:
        token, expiry = _request_new_token()
        _cache_token(token, expiry)
        log.info("Token generated at %s UTC; expires at %s UTC", _now_utc(), expiry)
        return token


def is_token_valid() -> bool:
    with _lock:
        token = _state["token"]
        expiry = _state["expiry"]
    return bool(token) and not _is_expired(expiry)


def refresh_token(force: bool = False) -> str:
    with _lock:
        if not force and is_token_valid():
            log.info("Using existing token")
            return _state["token"]
    log.info("Token expired → generating new token")
    return generate_token()


def get_token(force_refresh: bool = False) -> str:
    if force_refresh:
        return refresh_token(force=True)
    return refresh_token(force=False)


def get_headers() -> Dict[str, str]:
    client_id = _get_secret_value("CLIENT_ID")
    token = get_token()
    return {
        "access-token": token,
        "client-id": client_id,
        "Content-Type": "application/json",
    }

# -----------------------------------------------------------------------------
# Request helper with 401 auto-refresh
# -----------------------------------------------------------------------------
def request_with_auto_refresh(method: str, url: str, **kwargs) -> requests.Response:
    """
    Perform an HTTP request with automatic token handling.
    Retries once on 401 after forced token refresh.
    """
    headers = kwargs.pop("headers", {}) or {}
    headers.update(get_headers())
    resp = requests.request(method, url, headers=headers, timeout=HTTP_TIMEOUT, **kwargs)
    if resp.status_code != 401:
        return resp

    log.warning("Token refreshed due to 401")
    token = refresh_token(force=True)
    headers.update({
        "access-token": token,
    })
    log.info("Retrying request after token refresh")
    resp_retry = requests.request(method, url, headers=headers, timeout=HTTP_TIMEOUT, **kwargs)
    return resp_retry

# -----------------------------------------------------------------------------
# Backwards compatibility aliases
# -----------------------------------------------------------------------------
def get_access_token(force_refresh: bool = False) -> str:
    return get_token(force_refresh=force_refresh)

def clear_token():
    with _lock:
        _cache_token(None, None)  # type: ignore
