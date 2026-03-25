import time
import requests

from core.token_manager import get_headers

BASE_URL = "https://api.dhan.co/v2"


def _build_url(endpoint):
    if endpoint.startswith("http"):
        return endpoint
    return f"{BASE_URL}/{endpoint.lstrip('/')}"


def safe_post(endpoint, payload, retries=3, timeout=10):
    headers = get_headers()
    if not headers:
        return None, "Missing Dhan credentials"
    missing = []
    if not headers.get("access-token"):
        missing.append("access token")
    if not headers.get("client-id"):
        missing.append("client ID")
    if missing:
        return None, f"Missing Dhan {' and '.join(missing)}"

    last_error = None
    url = _build_url(endpoint)
    for attempt in range(retries):
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=timeout)
            if res.status_code >= 500:
                last_error = f"Server error {res.status_code}"
                time.sleep(1 + attempt)
                continue

            data = res.json()
            if res.status_code != 200:
                return None, data
            return data, None
        except Exception as exc:
            last_error = str(exc)
            time.sleep(1 + attempt)

    return None, last_error or "Request failed"


class DhanApiClient:
    def __init__(self, retries=3, timeout=10):
        self.retries = retries
        self.timeout = timeout

    def post(self, endpoint, payload):
        return safe_post(endpoint, payload, retries=self.retries, timeout=self.timeout)
