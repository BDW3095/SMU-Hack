"""Standalone validation: generates 4 style variants from a test image.
Usage: python -m pytest tests/test_image_agent.py -v  (requires AGNES_API_KEY in .env)
Or:    python tests/test_image_agent.py path/to/room.jpg
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dotenv import load_dotenv
load_dotenv()

import pytest
from unittest.mock import patch, MagicMock


SAMPLE_CONTEXT = {
    "room_type": "Living Room",
    "must_haves": ["A large L-shaped sofa", "Warm floor lamp", ""],
}


def _make_tiny_jpeg() -> bytes:
    from PIL import Image
    import io
    img = Image.new("RGB", (100, 100), color=(180, 160, 140))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_generate_style_calls_agnes_api():
    from agents.image_agent import ImageAgent

    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = {"data": [{"url": "https://example.com/img.jpg"}]}
    fake_response.raise_for_status = MagicMock()

    fake_download = b"\xff\xd8\xff" + b"\x00" * 100  # minimal jpeg-like bytes

    with patch("agents.image_agent.requests.post", return_value=fake_response), \
         patch("agents.image_agent.download_image_bytes", return_value=fake_download):
        agent = ImageAgent()
        result = agent.generate_style(_make_tiny_jpeg(), "Minimalist", "clean lines", SAMPLE_CONTEXT)

    assert isinstance(result, bytes)
    assert len(result) > 0


def test_generate_all_styles_returns_four():
    from agents.image_agent import ImageAgent, STYLES

    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = {"data": [{"url": "https://example.com/img.jpg"}]}
    fake_response.raise_for_status = MagicMock()
    fake_bytes = b"\xff\xd8\xff" + b"\x00" * 50

    with patch("agents.image_agent.requests.post", return_value=fake_response), \
         patch("agents.image_agent.download_image_bytes", return_value=fake_bytes):
        agent = ImageAgent()
        results = agent.generate_all_styles(_make_tiny_jpeg(), SAMPLE_CONTEXT)

    assert set(results.keys()) == set(STYLES.keys())
    for v in results.values():
        assert isinstance(v, bytes)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("image_path", nargs="?", default=None)
    args = parser.parse_args()

    if args.image_path:
        from agents.image_agent import ImageAgent
        with open(args.image_path, "rb") as f:
            img_bytes = f.read()
        print("Generating 4 styles (this may take ~60 s)…")
        results = ImageAgent().generate_all_styles(img_bytes, SAMPLE_CONTEXT)
        for style_name, out_bytes in results.items():
            out_path = f"test_output_{style_name.replace('/', '_').replace(' ', '_')}.jpg"
            with open(out_path, "wb") as f:
                f.write(out_bytes)
            print(f"  Saved: {out_path} ({len(out_bytes):,} bytes)")
        print("Done — open the saved images to verify quality.")
    else:
        print("No image path provided. Run with pytest for unit tests.")
