import time

import requests

from .domain import AutomationError


class HttpError(AutomationError):
    pass


class JsonClient:
    def __init__(self, timeout: float = 20, retries: int = 2, session=None, sleep=time.sleep):
        self.timeout = timeout
        self.retries = retries
        self.session = session or requests.Session()
        self.sleep = sleep

    def request(self, method: str, url: str, *, headers=None, payload=None, allow_not_found=False):
        for attempt in range(self.retries + 1):
            try:
                response = self.session.request(
                    method, url, headers=headers, json=payload,
                    timeout=(min(5, self.timeout), self.timeout), allow_redirects=False,
                )
            except (requests.Timeout, requests.ConnectionError):
                if attempt < self.retries:
                    self.sleep(2 ** attempt)
                    continue
                raise HttpError("network_unavailable") from None
            except requests.RequestException:
                raise HttpError("request_failed") from None
            if response.status_code == 404 and allow_not_found:
                return None
            if response.status_code == 429 or 500 <= response.status_code <= 599:
                if attempt < self.retries:
                    delay = 2 ** attempt
                    retry_after = response.headers.get("Retry-After", "")
                    if retry_after.isdigit():
                        delay = min(10, max(delay, int(retry_after)))
                    self.sleep(delay)
                    continue
            if not 200 <= response.status_code < 300:
                # Never include provider error bodies, headers, or URLs in output.
                raise HttpError(f"http_{response.status_code}")
            try:
                data = response.json()
            except ValueError:
                raise HttpError("response_invalid_json") from None
            if not isinstance(data, dict):
                raise HttpError("response_invalid_object")
            return data
        raise HttpError("request_failed")

    def close(self):
        self.session.close()
