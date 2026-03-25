import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from core.token_manager import get_headers

BASE_URL = "https://api.dhan.co/v2"

class DhanApiClient:
    def __init__(
        self,
        base_url=BASE_URL,
        timeout=10,
        max_retries=3,
        backoff_factor=0.3,
        status_forcelist=None,
        header_provider=None,
        session=None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.header_provider = header_provider or get_headers
        self.session = session or requests.Session()

        if session is None:
            retries = Retry(
                total=max_retries,
                backoff_factor=backoff_factor,
                status_forcelist=status_forcelist or [429, 500, 502, 503, 504],
                allowed_methods=frozenset(["POST"]),
                raise_on_status=False,
            )
            adapter = HTTPAdapter(max_retries=retries)
            self.session.mount("https://", adapter)
            self.session.mount("http://", adapter)

    def post(self, endpoint, payload):
        url = endpoint if endpoint.startswith("http") else f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = self.header_provider() or {}

        if not headers:
            return None, "Authentication failed: missing token or client ID"

        try:
            response = self.session.post(url, headers=headers, json=payload, timeout=self.timeout)
        except requests.RequestException as exc:
            return None, str(exc)

        if response.status_code != 200:
            return None, f"HTTP {response.status_code}"

        try:
            return response.json(), None
        except ValueError:
            return None, "Invalid JSON"
