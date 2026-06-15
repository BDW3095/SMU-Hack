import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

from clients.scrapeless_client import ScrapelessClient
from core.interfaces import ProductSearchProvider

_SHOPEE_REGION = "shopee.sg"


def _build_search_url(keyword: str, limit: int = 10) -> str:
    encoded = urllib.parse.quote(keyword)
    return (
        f"https://{_SHOPEE_REGION}/api/v4/search/search_items"
        f"?limit={limit}&newest=0&by=sales&keyword={encoded}&order=desc&page_type=search"
    )


def _parse_products(raw_items: list) -> list[dict]:
    """Extract, normalise and rank product data from the Scrapeless response.

    Shopee prices are stored as integer cents × 100000; the normalisation
    handles both that representation and plain-cent values.
    Sorted: highest rating first, then lowest price.
    """
    products = []
    for item in raw_items:
        try:
            basic = item.get("item_basic") or item
            name = basic.get("name", "")
            price_raw = basic.get("price", 0)
            price_sgd = round(price_raw / 100000, 2) if price_raw > 1000 else round(price_raw / 100, 2)
            rating_data = basic.get("item_rating", {})
            rating = rating_data.get("rating_star", 0) if isinstance(rating_data, dict) else 0
            item_id = basic.get("itemid") or basic.get("item_id", "")
            shop_id = basic.get("shopid") or basic.get("shop_id", "")
            image_hash = basic.get("image", "")
            image_url = (
                f"https://cf.shopee.sg/file/{image_hash}"
                if image_hash and not image_hash.startswith("http")
                else image_hash
            )
            product_url = (
                f"https://shopee.sg/product/{shop_id}/{item_id}"
                if item_id and shop_id
                else ""
            )
            if name and product_url:
                products.append({
                    "name": name,
                    "price_sgd": price_sgd,
                    "rating": rating,
                    "image_url": image_url,
                    "product_url": product_url,
                })
        except Exception:
            continue
    products.sort(key=lambda p: (-p["rating"], p["price_sgd"]))
    return products[:3]


def _fallback_link(keyword: str) -> list[dict]:
    encoded = urllib.parse.quote(keyword)
    return [{
        "name": f"Search '{keyword}' on Shopee",
        "price_sgd": None,
        "rating": None,
        "image_url": "",
        "product_url": f"https://shopee.sg/search?keyword={encoded}",
    }]


class ShopeeProductSearchProvider(ProductSearchProvider):
    """Implements ProductSearchProvider using the Scrapeless Shopee scraping API."""

    def __init__(self, client: ScrapelessClient) -> None:
        self._client = client

    def search(self, keyword: str) -> list[dict]:
        try:
            data = self._client.scrape(
                actor="scraper.shopee",
                input_data={"action": "shopee.search", "url": _build_search_url(keyword)},
            )
            raw_items = (
                data.get("data", {}).get("items", [])
                or data.get("result", {}).get("items", [])
                or data.get("items", [])
                or []
            )
            return _parse_products(raw_items)
        except Exception:
            return []

    def search_all(self, furniture_list: list[dict]) -> dict[str, list]:
        """Parallel search for every item. Returns {category: [top 3 products]}."""
        with ThreadPoolExecutor(max_workers=6) as ex:
            future_to_item = {
                ex.submit(self.search, item["shopee_keyword"]): item
                for item in furniture_list
            }
            results: dict[str, list] = {}
            for future in as_completed(future_to_item):
                item = future_to_item[future]
                products = future.result() or _fallback_link(item["shopee_keyword"])
                results[item["category"]] = products
        return results
