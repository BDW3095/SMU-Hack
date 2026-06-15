import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dotenv import load_dotenv
load_dotenv()

import pytest
from unittest.mock import patch, MagicMock


def _mock_submit(task_id="abc123"):
    m = MagicMock()
    m.status_code = 200
    m.json.return_value = {"taskId": task_id}
    m.raise_for_status = MagicMock()
    return m


def _mock_result(items: list):
    m = MagicMock()
    m.status_code = 200
    m.json.return_value = {"status": "completed", "data": {"items": items}}
    return m


SAMPLE_ITEMS = [
    {
        "item_basic": {
            "name": "3 Seater Sofa Linen",
            "price": 45000000,
            "item_rating": {"rating_star": 4.8},
            "itemid": 111,
            "shopid": 222,
            "image": "abc123hash",
        }
    },
    {
        "item_basic": {
            "name": "Budget Sofa Singapore",
            "price": 18000000,
            "item_rating": {"rating_star": 4.2},
            "itemid": 333,
            "shopid": 444,
            "image": "def456hash",
        }
    },
]


def test_search_returns_top_products():
    from services.shopee_service import ShopeeService

    with patch("services.shopee_service.requests.post", return_value=_mock_submit()), \
         patch("services.shopee_service.requests.get", return_value=_mock_result(SAMPLE_ITEMS)), \
         patch("services.shopee_service.time.sleep"), \
         patch.dict(os.environ, {"SCRAPELESS_API_KEY": "test-key"}):
        service = ShopeeService()
        results = service.search("3 seater sofa singapore")

    assert isinstance(results, list)
    assert len(results) <= 3
    assert results[0]["name"] == "3 Seater Sofa Linen"  # higher rating first


def test_search_returns_empty_on_missing_api_key():
    from services.shopee_service import ShopeeService
    with patch.dict(os.environ, {"SCRAPELESS_API_KEY": ""}):
        service = ShopeeService()
        results = service.search("anything")
    assert results == []


def test_search_all_returns_fallback_links_on_empty():
    from services.shopee_service import ShopeeService

    furniture = [
        {"name": "Rug", "category": "Rug", "shopee_keyword": "area rug singapore"},
    ]

    with patch.dict(os.environ, {"SCRAPELESS_API_KEY": "test-key"}), \
         patch("services.shopee_service.requests.post", return_value=_mock_submit()), \
         patch("services.shopee_service.requests.get", return_value=_mock_result([])), \
         patch("services.shopee_service.time.sleep"):
        service = ShopeeService()
        results = service.search_all(furniture)

    assert "Rug" in results
    assert "shopee.sg/search" in results["Rug"][0]["product_url"]
