import os
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

import pyotp
import requests

AUTH_URL = "https://auth.dhan.co/app/generateAccessToken"
HTTP_TIMEOUT = 10
TOTP_INTERVAL = 30
REFRESH_BUFFER = timedelta(minutes=3)
MAX_TOKEN_ATTEMPTS = 2

CLIENT_ID = os.getenv("CLIENT_ID", "").strip()
if not CLIENT_ID:
    raise RuntimeError("CLIENT_ID missing. Set environment variable.")

_state: Dict[str, Any] = {"token": None, "expiry": None}
_lock = threading.Lock()

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)

def _load_credentials() -> Tuple[str, str, str]:
    client_id = CLIENT_ID
    pin = os.getenv("DHAN_PIN", "").strip()
    totp_secret = os.getenv("TOTP_SECRET", "").strip()
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
    if expiry_raw is None:
        raise ValueError("expiryTime missing in response")
    try:
        ms = int(float(expiry_raw))
        return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)
    except Exception:
        dt_obj = datetime.fromisoformat(str(expiry_raw))
        if dt_obj.tzinfo is None:
            dt_obj = dt_obj.replace(tzinfo=timezone.utc)
        return dt_obj.astimezone(timezone.utc)

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

def _is_expired(expiry: Optional[datetime]) -> bool:
    if not expiry:
        return True
    return _now_utc() >= (expiry - REFRESH_BUFFER)

def refresh_token(force: bool = False) -> str:
    attempts = 0
    while attempts < MAX_TOKEN_ATTEMPTS:
        attempts += 1
        with _lock:
            token = _state["token"]
            expiry = _state["expiry"]
            if not force and token and not _is_expired(expiry):
                return token
            try:
                new_token, new_expiry = _request_new_token()
                _state["token"] = new_token
                _state["expiry"] = new_expiry
                return new_token
            except Exception:
                if attempts >= MAX_TOKEN_ATTEMPTS:
                    raise
                force = True
    raise RuntimeError("Token generation failed after retries")

def get_token(force_refresh: bool = False) -> str:
    token = refresh_token(force=force_refresh)
    if not token:
        raise RuntimeError("Token acquisition returned empty token")
    return token

def get_headers() -> Dict[str, str]:
    token = get_token()
    if not token:
        token = refresh_token(force=True)

    headers = {
        "access-token": token,
        "client-id": CLIENT_ID,
        "dhanClientId": CLIENT_ID,
        "Content-Type": "application/json",
    }

    # Debug prints (safe masked)
    print("AUTH DEBUG → CLIENT_ID:", CLIENT_ID)
    print("AUTH DEBUG → TOKEN:", token[:10], "...")

    return headers
