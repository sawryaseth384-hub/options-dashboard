import time
import requests

from core.token_manager import get_headers

BASE_URL = "https://api.dhan.co/v2"


class DhanApiClient:
    def __init__(self, base_url=BASE_URL, timeout=10, retries=2, backoff=0.5):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff

    def post(self, endpoint, payload, timeout=None):
        headers = get_headers()
        if not headers:
            return None, "Missing Dhan credentials"

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        last_error = None

        for attempt in range(self.retries + 1):
            try:
                response = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=timeout or self.timeout,
                )

                if response.status_code == 200:
                    try:
                        return response.json(), None
                    except ValueError:
                        last_error = "Invalid JSON response"
                else:
                    last_error = f"HTTP {response.status_code}"
            except requests.RequestException as exc:
                last_error = str(exc)

            if attempt < self.retries:
                time.sleep(self.backoff * (2**attempt))

        return None, last_error
