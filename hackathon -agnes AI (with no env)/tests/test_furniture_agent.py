import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dotenv import load_dotenv
load_dotenv()

import json
import pytest
from unittest.mock import patch, MagicMock


SAMPLE_CONTEXT = {
    "room_type": "Living Room",
    "must_haves": ["Large comfy sofa", "Good reading light", "Storage for books"],
}


def _fake_agnes_response(content: str):
    m = MagicMock()
    m.status_code = 200
    m.json.return_value = {"choices": [{"message": {"content": content}}]}
    m.raise_for_status = MagicMock()
    return m


def test_generate_list_returns_valid_items():
    from agents.furniture_agent import FurnitureAgent

    sample_items = [
        {"name": "3-seat sofa", "category": "Sofa", "shopee_keyword": "3 seater sofa singapore"},
        {"name": "Floor lamp", "category": "Floor Lamp", "shopee_keyword": "floor lamp singapore"},
    ]
    fake_resp = _fake_agnes_response(json.dumps(sample_items))

    with patch("agents.furniture_agent.requests.post", return_value=fake_resp):
        agent = FurnitureAgent()
        result = agent.generate_list(SAMPLE_CONTEXT)

    assert isinstance(result, list)
    assert len(result) >= 1
    assert "name" in result[0]
    assert "shopee_keyword" in result[0]


def test_generate_list_falls_back_on_invalid_json():
    from agents.furniture_agent import FurnitureAgent, _FALLBACK_LIST

    fake_resp = _fake_agnes_response("not valid json {{{{")

    with patch("agents.furniture_agent.requests.post", return_value=fake_resp):
        agent = FurnitureAgent()
        result = agent.generate_list(SAMPLE_CONTEXT)

    assert result == _FALLBACK_LIST


def test_generate_list_strips_markdown_fences():
    from agents.furniture_agent import FurnitureAgent

    items = [{"name": "Rug", "category": "Rug", "shopee_keyword": "rug singapore"}]
    content_with_fences = f"```json\n{json.dumps(items)}\n```"
    fake_resp = _fake_agnes_response(content_with_fences)

    with patch("agents.furniture_agent.requests.post", return_value=fake_resp):
        agent = FurnitureAgent()
        result = agent.generate_list(SAMPLE_CONTEXT)

    assert result[0]["category"] == "Rug"
