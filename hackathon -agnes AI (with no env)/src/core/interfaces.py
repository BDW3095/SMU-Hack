from abc import ABC, abstractmethod


class ImageGenerationProvider(ABC):
    """Generates a redesigned room image from raw image bytes and a text prompt."""

    @abstractmethod
    def generate(self, image_bytes: bytes, prompt: str) -> bytes:
        ...


class FurnitureListProvider(ABC):
    """Produces a shoppable furniture list from room context (room type + must-haves)."""

    @abstractmethod
    def generate_list(self, context: dict) -> list[dict]:
        ...


class ProductSearchProvider(ABC):
    """Returns ranked product listings for a search keyword."""

    @abstractmethod
    def search(self, keyword: str) -> list[dict]:
        ...


class EmailSender(ABC):
    """Sends the chosen room design and shopping list to a recipient email address."""

    @abstractmethod
    def send(
        self,
        to_email: str,
        chosen_style: str,
        image_bytes: bytes,
        shopee_results: dict[str, list],
    ) -> None:
        ...
