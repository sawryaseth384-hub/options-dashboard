import time
import requests

from core.token_manager import get_headers


class DhanApiClient:
    def __init__(self, base_url="https://api.dhan.co/v2", headers_provider=None, timeout=8, retries=2, backoff=1.0):
        self.base_url = base_url.rstrip("/")
        self.headers_provider = headers_provider or get_headers
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff

    def post(self, endpoint, payload):
        return self._request("post", endpoint, json=payload)

    def _request(self, method, endpoint, json=None):
        url = endpoint if endpoint.startswith("http") else f"{self.base_url}/{endpoint.lstrip('/')}"
        last_error = None
        for attempt in range(self.retries + 1):
            try:
                headers = self.headers_provider() or {}
                response = requests.request(method, url, headers=headers, json=json, timeout=self.timeout)
                if response.status_code != 200:
                    last_error = f"HTTP {response.status_code}"
                else:
                    try:
                        return response.json(), None
                    except Exception as exc:
                        last_error = f"Invalid JSON: {exc}"
            except Exception as exc:
                last_error = str(exc)
            if attempt < self.retries:
                time.sleep(self.backoff * (attempt + 1))
        return None, last_error


def safe_post(url, payload, **kwargs):
    client = DhanApiClient(**kwargs)
    return client.post(url, payload)
