from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

VALID_IMAGE_SIZES = ("1K", "2K", "4K")

class ConfigError(RuntimeError):
    pass

@dataclass(frozen=True)
class Settings:
    api_key: str
    image_model: str = "gemini-3-pro-image-preview"
    planner_model: str = "gemini-3-flash-preview"
    image_size: str = "2K"
    output_dir: Path = Path("outputs")

    @classmethod
    def from_env(cls) -> "Settings":
        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise ConfigError("GEMINI_API_KEY not set.")
        size = os.environ.get("RENOVATION_IMAGE_SIZE", "2K").upper()
        if size not in VALID_IMAGE_SIZES:
            raise ConfigError(f"RENOVATION_IMAGE_SIZE must be one of {VALID_IMAGE_SIZES}, got {size!r}")
        return cls(
            api_key=key,
            image_model=os.environ.get("RENOVATION_IMAGE_MODEL", cls.image_model),
            planner_model=os.environ.get("RENOVATION_PLANNER_MODEL", cls.planner_model),
            image_size=size,
            output_dir=Path(os.environ.get("RENOVATION_OUTPUT_DIR", "outputs")),
        )
