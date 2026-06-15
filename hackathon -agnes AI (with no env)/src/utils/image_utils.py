"""Pure image transformation utilities — no config, no business logic."""

import base64
import io

import requests
from PIL import Image


def to_base64_data_url(image_bytes: bytes, mime: str = "image/jpeg") -> str:
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


def download_image_bytes(url: str) -> bytes:
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.content


def upload_to_imgbb(image_bytes: bytes, api_key: str) -> str:
    """Upload to imgbb and return the public URL (fallback for APIs that reject data URLs)."""
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    resp = requests.post(
        "https://api.imgbb.com/1/upload",
        data={"key": api_key, "image": encoded},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["data"]["url"]


def normalize_to_jpeg(image_bytes: bytes) -> bytes:
    """Convert any uploaded image format to JPEG bytes for consistent API input."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()
