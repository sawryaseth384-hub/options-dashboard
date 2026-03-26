import os
import threading
import requests
import pyotp
from datetime import datetime, timedelta, timezone

try:
    import streamlit as st
except Exception:
    st = None

# =========================
# CONFIG
# =========================
AUTH_URL = "https://auth.dhan.co/app/generateAccessToken"
# Refresh a few minutes early to avoid race conditions at expiry
REFRESH_BUFFER = timedelta(minutes=3)
# Dhan tokens are valid for 24h; use as fallback if API doesn’t return expiry
DEFAULT_TTL = timedelta(hours=24)

# =========================
# STATE (IN-MEMORY)
# =========================
_state = {
    "token": None,
    "expiry": None,
}
_lock = threading.Lock()

# =========================
# HELPERS
# =========================
def _get_secret(key: str) -> str:
    """Streamlit secrets → env var fallback."""
    if st:
        try:
            val = st.secrets.get(key)
            if val:
                return str(val).strip()
        except Exception:
            pass
    return os.getenv(key, "").strip()

def _load_credentials():
    client_id = _get_secret("CLIENT_ID")
    pin = _get_secret("DHAN_PIN")
    totp_secret = _get_secret("TOTP_SECRET")

    if not client_id or not pin or not totp_secret:
        raise RuntimeError("Missing CLIENT_ID / DHAN_PIN / TOTP_SECRET")

    return client_id, pin, totp_secret

def _generate_totp(secret: str) -> str:
    return pyotp.TOTP(secret).now()

def _parse_expiry(expiry_raw):
    """
    Accepts ISO string or epoch seconds/millis.
    Returns timezone-aware datetime.
    """
    if expiry_raw is None:
        return datetime.now(timezone.utc) + DEFAULT_TTL

    # ISO-8601 string
    if isinstance(expiry_raw, str):
        try:
            dt = datetime.fromisoformat(expiry_raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            pass

    # Numeric epoch (seconds or millis)
    try:
        expiry_raw = int(expiry_raw)
        # Heuristic: if too large, treat as millis
        if expiry_raw > 4_000_000_000:  # ~year 2100 in seconds
            expiry_raw = expiry_raw / 1000
        return datetime.fromtimestamp(expiry_raw, tz=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc) + DEFAULT_TTL

def _is_token_expired() -> bool:
    expiry = _state["expiry"]
    if not expiry:
        return True
    return datetime.now(timezone.utc) >= (expiry - REFRESH_BUFFER)

# =========================
# TOKEN GENERATION
# =========================
def _generate_token() -> str:
    client_id, pin, totp_secret = _load_credentials()
    totp = _generate_totp(totp_secret)

    payload = {
        "dhanClientId": client_id,
        "pin": pin,
        "totp": totp,
    }

    res = requests.post(AUTH_URL, params=payload, timeout=10)
    if res.status_code != 200:
        raise RuntimeError(f"Auth failed: {res.status_code} - {res.text}")

    data = res.json() if res.content else {}
    token = data.get("accessToken")
    expiry_raw = data.get("expiryTime")

    if not token:
        raise RuntimeError("Invalid token response: accessToken missing")

    expiry_dt = _parse_expiry(expiry_raw)

    _state["token"] = token
    _state["expiry"] = expiry_dt
    return token

# =========================
# PUBLIC FUNCTIONS
# =========================
def get_token() -> str:
    """
    Returns a valid token, generating/refreshing if needed.
    Thread-safe for concurrent callers.
    """
    with _lock:
        if _state["token"] and not _is_token_expired():
            return _state["token"]
        return _generate_token()

def refresh_token() -> str:
    """
    Forces a token refresh regardless of current validity.
    """
    with _lock:
        return _generate_token()

def is_token_valid() -> bool:
    with _lock:
        return _state["token"] is not None and not _is_token_expired()

def get_headers() -> dict:
    client_id, _, _ = _load_credentials()
    token = get_token()
    return {
        "access-token": token,
        "client-id": client_id,
        "Content-Type": "application/json",
    }

# =========================
# OPTIONAL: 401 HANDLER
# =========================
def handle_401_and_refresh():
    """
    Convenience helper: call when an API request returns 401.
    """
    return refresh_token()
