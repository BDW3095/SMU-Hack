import base64
import itertools
import threading

import requests

from config import Config
from utils.image_utils import to_base64_data_url, upload_to_imgbb, download_image_bytes


class AgnesClient:
    """Low-level HTTP client for the Agnes AI API.

    Responsible only for making HTTP calls and returning raw data — no prompt
    building, no JSON parsing, no business logic.
    """

    IMAGE_MODEL = "agnes-image-2.0-flash"
    CHAT_MODEL = "agnes-2.0-flash"
    IMAGE_ENDPOINT = "/v1/images/generations"
    CHAT_ENDPOINT = "/v1/chat/completions"

    def __init__(self, config: Config) -> None:
        self._config = config
        self._key_cycle = itertools.cycle(config.agnes_api_keys)
        self._key_lock = threading.Lock()

    def _next_key(self) -> str:
        """Thread-safe round-robin key selection."""
        with self._key_lock:
            return next(self._key_cycle)

    def _headers(self, key: str) -> dict:
        return {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

    @property
    def _auth_headers(self) -> dict:
        return self._headers(self._config.agnes_api_key)

    def _post(self, endpoint: str, payload: dict, timeout: int = 90) -> requests.Response:
        resp = requests.post(
            f"{self._config.agnes_base_url}{endpoint}",
            headers=self._auth_headers,
            json=payload,
            timeout=timeout,
            allow_redirects=False,
        )
        resp.raise_for_status()
        return resp

    def _extract_image_bytes(self, response: requests.Response) -> bytes:
        """Handle both URL and base64 response formats from Agnes."""
        data = response.json()["data"][0]
        if "url" in data:
            return download_image_bytes(data["url"])
        if "b64_json" in data:
            return base64.b64decode(data["b64_json"])
        raise ValueError(f"Unrecognised Agnes image response keys: {list(data.keys())}")

    def generate_image(self, image_bytes: bytes, prompt: str) -> bytes:
        """POST /v1/images/generations. Returns generated image bytes.

        Each call picks the next API key in round-robin order so parallel
        image generation calls hit different keys (avoids per-key rate limits).

        Tries image-to-image with base64 input first; falls back to imgbb
        public URL if the API rejects the base64 data URL (400/422).
        If neither works, falls back to pure text-to-image.
        """
        key = self._next_key()
        headers = self._headers(key)
        base64_input = to_base64_data_url(image_bytes)
        url = f"{self._config.agnes_base_url}{self.IMAGE_ENDPOINT}"

        # Attempt 1: image-to-image with base64 data URL
        payload = {
            "model": self.IMAGE_MODEL,
            "prompt": prompt,
            "size": "1024x1024",
            "image": base64_input,
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=600, allow_redirects=False)

        # Attempt 2: if base64 rejected, try imgbb public URL
        if resp.status_code in (400, 422) and self._config.imgbb_api_key:
            try:
                public_url = upload_to_imgbb(image_bytes, self._config.imgbb_api_key)
                payload["image"] = public_url
                resp = requests.post(url, headers=headers, json=payload, timeout=600, allow_redirects=False)
            except Exception:
                pass

        # Attempt 3: fall back to text-to-image if image input still rejected
        if resp.status_code in (400, 422):
            payload.pop("image", None)
            resp = requests.post(url, headers=headers, json=payload, timeout=600, allow_redirects=False)

        resp.raise_for_status()
        return self._extract_image_bytes(resp)

    def chat_completion(self, messages: list[dict], temperature: float = 0.7) -> str:
        """POST /v1/chat/completions. Returns the assistant message content string."""
        resp = self._post(
            self.CHAT_ENDPOINT,
            {"model": self.CHAT_MODEL, "messages": messages, "temperature": temperature},
            timeout=30,
        )
        return resp.json()["choices"][0]["message"]["content"].strip()
