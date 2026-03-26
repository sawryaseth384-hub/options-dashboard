import logging
import time

try:
    import streamlit as st
except Exception:  # pragma: no cover - streamlit not available in some contexts
    st = None

from utils.secrets import get_secret

_logger = logging.getLogger(__name__)

TOKEN_SESSION_KEY = "dhan_access_token"
TOKEN_EXPIRY_KEY = "dhan_access_token_expiry"

_TOKEN_LOGGED = False
_TOKEN_STATUS_LOGGED = False
_CLIENT_ID_STATUS_LOGGED = False
_TOKEN_MISSING_WARNED = False
_TOKEN_EXPIRED_WARNED = False
_SECRETS_WARNED = False
_TOKEN_CACHE = {"token": None, "expires_at": None}


def _show_streamlit_error(message):
    if st is None:
        return
    try:
        st.error(message)
    except Exception:
        pass


def _get_secret_value(key):
    value = get_secret(key)
    return str(value).strip() if value else ""


def get_credential_status():
    client_id = _get_secret_value("CLIENT_ID")
    token = _get_secret_value("DHAN_ACCESS_TOKEN")
    return client_id, token


def _report_missing_secrets():
    global _SECRETS_WARNED
    if _SECRETS_WARNED:
        return
    client_id = _get_secret_value("CLIENT_ID")
    token = _get_secret_value("DHAN_ACCESS_TOKEN")
    missing = [name for name, value in {"CLIENT_ID": client_id, "DHAN_ACCESS_TOKEN": token}.items() if not value]
    if not missing:
        return
    _SECRETS_WARNED = True
    _logger.warning("Missing credentials: %s", ", ".join(missing))
    _show_streamlit_error(
        f"Missing credentials. Set {', '.join(missing)} in Streamlit secrets or environment variables."
    )


def _report_missing_token():
    global _TOKEN_MISSING_WARNED
    if _TOKEN_MISSING_WARNED:
        return
    _TOKEN_MISSING_WARNED = True
    _logger.warning("Missing Dhan access token.")
    _show_streamlit_error(
        "Missing access token. Set CLIENT_ID and DHAN_ACCESS_TOKEN in Streamlit secrets or environment variables."
    )


def _report_expired_token():
    global _TOKEN_EXPIRED_WARNED
    if _TOKEN_EXPIRED_WARNED:
        return
    _TOKEN_EXPIRED_WARNED = True
    _logger.warning("Cached access token expired.")
    _show_streamlit_error("Token expired. Update DHAN_ACCESS_TOKEN in Streamlit secrets.")


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


def _log_client_id_status(client_id):
    global _CLIENT_ID_STATUS_LOGGED
    if _CLIENT_ID_STATUS_LOGGED:
        return
    _CLIENT_ID_STATUS_LOGGED = True
    _logger.info("CLIENT_ID loaded: %s", "yes" if client_id else "no")


def _log_token_status(token):
    global _TOKEN_STATUS_LOGGED
    if _TOKEN_STATUS_LOGGED:
        return
    _TOKEN_STATUS_LOGGED = True
    _logger.info("DHAN_ACCESS_TOKEN loaded: %s", "yes" if token else "no")


def _get_cached_token():
    token = _TOKEN_CACHE.get("token")
    expires_at = _TOKEN_CACHE.get("expires_at")
    if token:
        return token, expires_at
    if st is None:
        return None, None
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
    _TOKEN_CACHE["token"] = token
    _TOKEN_CACHE["expires_at"] = expires_at
    if st is None:
        return
    try:
        st.session_state[TOKEN_SESSION_KEY] = token
        if expires_at is not None:
            st.session_state[TOKEN_EXPIRY_KEY] = expires_at
    except Exception:
        pass


def _is_expired(expires_at):
    if not expires_at:
        return False
    try:
        return time.time() >= float(expires_at)
    except Exception:
        return False


def get_access_token(force_refresh=False):
    cached_token, expires_at = _get_cached_token()
    if cached_token and _is_expired(expires_at):
        clear_token()
        _report_expired_token()
        cached_token = None
    if cached_token and not force_refresh:
        _log_token_status(cached_token)
        return cached_token
    configured_token = _get_secret_value("DHAN_ACCESS_TOKEN")
    if configured_token:
        _cache_token(configured_token, expires_at)
        _log_token_once(configured_token)
        _log_token_status(configured_token)
        return configured_token
    _report_missing_secrets()
    _report_missing_token()
    _log_token_status(None)
    return None


def get_token(force_refresh=False):
    """Deprecated: legacy alias for get_access_token."""
    return get_access_token(force_refresh=force_refresh)


def get_client_id():
    client_id = _get_secret_value("CLIENT_ID")
    if not client_id:
        _report_missing_secrets()
    _log_client_id_status(client_id)
    return client_id or None


def get_credentials():
    client_id = _get_secret_value("CLIENT_ID")
    token = _get_secret_value("DHAN_ACCESS_TOKEN")
    credentials = {"CLIENT_ID": client_id, "DHAN_ACCESS_TOKEN": token}
    missing = [name for name, value in credentials.items() if not value]
    if missing:
        _logger.debug("Missing credentials: %s", ", ".join(missing))
        _logger.warning("Missing required credentials.")
        return {"_error": "Missing required credentials"}
    return credentials


def clear_token():
    _TOKEN_CACHE["token"] = None
    _TOKEN_CACHE["expires_at"] = None
    if st is None:
        return
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
    return headers
