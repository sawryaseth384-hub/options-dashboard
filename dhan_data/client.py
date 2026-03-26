import logging
import time

import requests

from core import token_manager

BASE_URL = "https://api.dhan.co"


def _full_url(path):
    path = path.lstrip("/")
    return f"{BASE_URL}/{path}"


_logger = logging.getLogger(__name__)


def _auth_error(message):
    return {"_error": message}, message


class DhanApiClient:
    def __init__(self, base_url=BASE_URL, retries=3, timeout=10):
        self.base_url = base_url
        self.retries = retries
        self.timeout = timeout
        self.token = token_manager.get_token()

    def get_headers(self, extra=None):
        headers = {"Content-Type": "application/json"}
        token = self.token or token_manager.get_token()
        if token:
            self.token = token
            headers["access-token"] = token
        if extra:
            headers.update(extra)
        return headers

    def refresh_token(self):
        self.token = token_manager.get_token(force_refresh=True)
        return self.token

    def request(self, method, url, payload=None, params=None, headers=None, timeout=None):
        resolved_url = url if url.startswith("http") else _full_url(url)
        resolved_headers = self.get_headers(headers)
        if "access-token" not in resolved_headers:
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


_DEFAULT_CLIENT = None


def _get_default_client():
    global _DEFAULT_CLIENT
    if _DEFAULT_CLIENT is None:
        _DEFAULT_CLIENT = DhanApiClient()
    return _DEFAULT_CLIENT


def safe_request(method, url, client, payload=None, params=None, headers=None, retries=None, timeout=None):
    attempts = retries or getattr(client, "retries", 3) or 3
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
        if attempt < attempts:
            time.sleep(0.5 * attempt)
    _logger.warning("Request failed after %s attempts: %s", attempts, last_error)
    return {}, last_error


def safe_post(url, payload, headers=None, retries=3, timeout=10):
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


def safe_get(url, headers=None, params=None, retries=3, timeout=5):
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
