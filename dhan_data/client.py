import time
import requests
from core.token_manager import get_headers

BASE_URL = "https://api.dhan.co/v2"


def _full_url(path):
    path = path.lstrip("/")
    return f"{BASE_URL}/{path}"


def safe_post(url, payload, headers=None, retries=3, timeout=10):
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            res = requests.post(
                url,
                headers=headers or get_headers(),
                json=payload,
                timeout=timeout
            )
            if res.status_code != 200:
                last_error = f"HTTP {res.status_code}"
            else:
                try:
                    return res.json(), None
                except Exception as exc:
                    last_error = f"Invalid JSON response: {exc}"
        except Exception as exc:
            last_error = str(exc)
        if attempt < retries:
            time.sleep(0.5 * attempt)
    return None, last_error


def safe_get(url, headers=None, params=None, retries=3, timeout=5):
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            res = requests.get(
                url,
                headers=headers or get_headers(),
                params=params,
                timeout=timeout
            )
            if res.status_code != 200:
                last_error = f"HTTP {res.status_code}"
            else:
                try:
                    return res.json(), None
                except Exception:
                    last_error = "Invalid JSON response"
        except Exception as exc:
            last_error = str(exc)
        if attempt < retries:
            time.sleep(0.5 * attempt)
    return None, last_error


class DhanApiClient:
    def __init__(self, base_url=BASE_URL, retries=3, timeout=10):
        self.base_url = base_url
        self.retries = retries
        self.timeout = timeout

    def post(self, endpoint, payload):
        return safe_post(
            _full_url(endpoint),
            payload,
            retries=self.retries,
            timeout=self.timeout
        )

    def get(self, endpoint, params=None):
        return safe_get(
            _full_url(endpoint),
            params=params,
            retries=self.retries,
            timeout=self.timeout
        )
