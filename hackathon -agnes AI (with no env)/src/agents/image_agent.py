from concurrent.futures import ThreadPoolExecutor, as_completed

from clients.agnes_client import AgnesClient
from core.interfaces import ImageGenerationProvider
from utils.image_utils import normalize_to_jpeg

STYLES: dict[str, str] = {
    "Minimalist": (
        "minimalist design, clean lines, white and light grey tones, uncluttered, "
        "negative space, Muji aesthetic"
    ),
    "Scandinavian": (
        "Scandinavian hygge style, warm birch wood tones, soft textiles, "
        "neutral white palette, cosy atmosphere"
    ),
    "Modern Industrial": (
        "modern industrial loft, exposed concrete, metal accents, charcoal and "
        "warm amber tones, Edison bulb lighting"
    ),
    "Tropical / Rattan": (
        "tropical Bali resort style, natural rattan and cane furniture, lush "
        "indoor plants, warm earthy sandy tones"
    ),
}


def _build_prompt(style_desc: str, context: dict) -> str:
    must_haves = [m for m in context.get("must_haves", []) if m.strip()]
    must_have_str = ". ".join(must_haves) + "." if must_haves else ""
    return (
        f"Professional interior redesign of this {context['room_type']}. "
        f"Style: {style_desc}. "
        f"{must_have_str} "
        "Photorealistic render, professional interior photography lighting, high resolution. "
        "Preserve existing room architecture, window positions, and floor plan structure."
    ).strip()


class AgnesImageProvider(ImageGenerationProvider):
    """Implements ImageGenerationProvider using the Agnes Image 2.0 Flash model."""

    def __init__(self, client: AgnesClient) -> None:
        self._client = client

    def generate(self, image_bytes: bytes, prompt: str) -> bytes:
        return self._client.generate_image(image_bytes, prompt)


class ImageAgent:
    """Orchestrates parallel image generation across all style variants.

    Depends on ImageGenerationProvider so the underlying model is swappable
    without modifying this class (Open/Closed).
    """

    def __init__(self, provider: ImageGenerationProvider) -> None:
        self._provider = provider

    def generate_style(
        self, image_bytes: bytes, style_name: str, style_desc: str, context: dict
    ) -> bytes:
        jpeg_bytes = normalize_to_jpeg(image_bytes)
        prompt = _build_prompt(style_desc, context)
        return self._provider.generate(jpeg_bytes, prompt)

    def generate_all_styles(
        self, image_bytes: bytes, context: dict
    ) -> dict[str, bytes]:
        """Generate all 4 style variants concurrently. Returns {style_name: image_bytes}."""
        with ThreadPoolExecutor(max_workers=4) as ex:
            future_to_style = {
                ex.submit(self.generate_style, image_bytes, name, desc, context): name
                for name, desc in STYLES.items()
            }
            results = {
                future_to_style[f]: f.result() for f in as_completed(future_to_style)
            }
        return {name: results[name] for name in STYLES if name in results}
