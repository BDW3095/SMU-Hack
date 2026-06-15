import time

import requests

from config import Config

_SUBMIT_URL = "https://api.scrapeless.com/api/v1/scraper/request"
_RESULT_URL = "https://api.scrapeless.com/api/v1/scraper/result/{task_id}"

_TERMINAL_OK = {"completed", "success", "finished"}
_TERMINAL_ERR = {"failed", "error"}


class ScrapelessClient:
    """Low-level HTTP client for the Scrapeless scraping API.

    Responsible only for submitting jobs, polling for results, and returning
    raw response data — no parsing, no business logic.
    """

    POLL_INTERVAL = 1.0
    POLL_TIMEOUT = 12.0

    def __init__(self, config: Config) -> None:
        self._config = config

    @property
    def _headers(self) -> dict:
        return {
            "x-api-token": self._config.scrapeless_api_key,
            "Content-Type": "application/json",
        }

    def scrape(self, actor: str, input_data: dict) -> dict:
        """Submit a scraping job and poll until complete. Returns raw result dict.

        Returns an empty dict if the API key is missing, the job fails, or
        the polling window expires.
        """
        if not self._config.scrapeless_api_key:
            return {}

        resp = requests.post(
            _SUBMIT_URL,
            headers=self._headers,
            json={"actor": actor, "input": input_data},
            timeout=15,
        )
        resp.raise_for_status()

        task_id = resp.json().get("taskId") or resp.json().get("task_id", "")
        if not task_id:
            return {}

        deadline = time.time() + self.POLL_TIMEOUT
        while time.time() < deadline:
            time.sleep(self.POLL_INTERVAL)
            result = requests.get(
                _RESULT_URL.format(task_id=task_id),
                headers=self._headers,
                timeout=15,
            )
            if result.status_code == 200:
                data = result.json()
                status = data.get("status", "")
                if status in _TERMINAL_OK:
                    return data
                if status in _TERMINAL_ERR:
                    return {}

        return {}
