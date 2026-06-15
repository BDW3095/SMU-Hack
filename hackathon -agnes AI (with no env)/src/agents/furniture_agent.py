import json
import re

from clients.agnes_client import AgnesClient
from core.interfaces import FurnitureListProvider

_SYSTEM_PROMPT = (
    "You are an expert interior designer for Singaporean homes. "
    "You create specific, shoppable furniture lists for room redesigns. "
    "Always respond with valid JSON only — no markdown fences, no explanation."
)

_FALLBACK_LIST: list[dict] = [
    {"name": "3-seater fabric sofa", "category": "Sofa", "shopee_keyword": "3 seater sofa fabric singapore"},
    {"name": "Wooden coffee table", "category": "Coffee Table", "shopee_keyword": "coffee table wood singapore"},
    {"name": "Floor lamp warm light", "category": "Floor Lamp", "shopee_keyword": "floor lamp warm light singapore"},
    {"name": "Area rug 160x230cm", "category": "Rug", "shopee_keyword": "area rug living room singapore"},
    {"name": "Open bookshelf 5-tier", "category": "Shelving", "shopee_keyword": "bookshelf open shelving singapore"},
]


def _build_user_prompt(context: dict) -> str:
    must_haves = [m for m in context.get("must_haves", []) if m.strip()]
    must_have_lines = (
        "\n".join(f"{i + 1}. {m}" for i, m in enumerate(must_haves))
        if must_haves
        else "No specific must-haves provided."
    )
    return (
        f"A {context['room_type']} is being redesigned across 4 styles: "
        "Minimalist, Scandinavian, Modern Industrial, and Tropical/Rattan.\n\n"
        f"The client's must-haves:\n{must_have_lines}\n\n"
        "Generate a comprehensive furniture and decor list of 6–10 items that would "
        "appear in this redesigned room. Focus on items a Singaporean would buy on Shopee SG.\n\n"
        "Return a JSON array. Each item:\n"
        '{"name": "descriptive item name", "category": "item type", '
        '"shopee_keyword": "Shopee SG search term under 50 chars"}'
    )


def _parse_response(raw: str) -> list[dict]:
    """Strip accidental markdown fences and parse JSON."""
    cleaned = re.sub(r"^```[a-z]*\n?", "", raw.strip())
    cleaned = re.sub(r"\n?```$", "", cleaned)
    items = json.loads(cleaned)
    if not isinstance(items, list) or not items:
        raise ValueError("Empty or non-list JSON response")
    return items


class AgnesFurnitureProvider(FurnitureListProvider):
    """Implements FurnitureListProvider using the Agnes 2.0 Flash chat model."""

    def __init__(self, client: AgnesClient) -> None:
        self._client = client

    def generate_list(self, context: dict) -> list[dict]:
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(context)},
        ]
        for _ in range(2):
            try:
                raw = self._client.chat_completion(messages)
                return _parse_response(raw)
            except Exception:
                continue
        return _FALLBACK_LIST
