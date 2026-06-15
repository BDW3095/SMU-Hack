import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Config:
    """Single source of truth for all environment-sourced settings.

    Frozen so nothing can accidentally mutate config after startup.
    """

    agnes_api_keys: tuple[str, ...]  # all keys; tuple is hashable and works with frozen
    agnes_base_url: str
    scrapeless_api_key: str
    gmail_sender: str
    gmail_password: str
    imgbb_api_key: str

    @property
    def agnes_api_key(self) -> str:
        """First key — used by chat_completion which doesn't need rotation."""
        return self.agnes_api_keys[0] if self.agnes_api_keys else ""

    @classmethod
    def from_env(cls) -> "Config":
        raw = os.getenv("AGNES_API_KEY", "")
        keys = tuple(k.strip() for k in raw.split(",") if k.strip())
        return cls(
            agnes_api_keys=keys or ("",),
            agnes_base_url=os.getenv("AGNES_BASE_URL", "https://apihub.agnes-ai.com"),
            scrapeless_api_key=os.getenv("SCRAPELESS_API_KEY", ""),
            gmail_sender=os.getenv("GMAIL_SENDER_EMAIL", ""),
            gmail_password=os.getenv("GMAIL_APP_PASSWORD", "").replace(" ", ""),
            imgbb_api_key=os.getenv("IMGBB_API_KEY", ""),
        )
