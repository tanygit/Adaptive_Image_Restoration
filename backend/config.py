"""
config.py - all backend settings in one place (environment variables with safe defaults).

Paths are resolved relative to this file, never to a user-specific absolute path.
Copy .env.example to .env (or set real environment variables) to override anything.
Class thresholds are NOT configured here: they live only in artifacts/class_thresholds.json.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def _load_dotenv(path: Path) -> None:
    """Tiny .env reader (KEY=VALUE lines); real environment variables always win."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(BASE_DIR / ".env")


def _path(name: str, default: str) -> Path:
    p = Path(os.environ.get(name, default))
    return p if p.is_absolute() else (BASE_DIR / p).resolve()


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name} must be an integer, got {raw!r}") from exc
    if value <= 0:
        raise ValueError(f"Environment variable {name} must be positive, got {value}")
    return value


@dataclass(frozen=True)
class Settings:
    artifacts_dir: Path
    restored_dir: Path
    max_upload_bytes: int          # hard limit on the raw uploaded file
    max_image_side: int            # max width or height in pixels
    min_image_side: int
    max_pixels: int                # max width * height
    inline_base64_max_bytes: int   # "auto" mode embeds the PNG only up to this size
    restored_ttl_seconds: int      # restored files older than this are deleted
    max_concurrent_jobs: int       # simultaneous restorations (CPU-bound work)
    device: str | None             # None = cuda if available else cpu


def load_settings() -> Settings:
    return Settings(
        artifacts_dir=_path("ARTIFACTS_DIR", "artifacts"),
        restored_dir=_path("RESTORED_DIR", "restored_images"),
        max_upload_bytes=_int("MAX_UPLOAD_BYTES", 25 * 1024 * 1024),
        max_image_side=_int("MAX_IMAGE_SIDE", 8000),
        min_image_side=_int("MIN_IMAGE_SIDE", 32),
        max_pixels=_int("MAX_PIXELS", 16_000_000),
        inline_base64_max_bytes=_int("INLINE_BASE64_MAX_BYTES", 3 * 1024 * 1024),
        restored_ttl_seconds=_int("RESTORED_TTL_SECONDS", 3600),
        max_concurrent_jobs=_int("MAX_CONCURRENT_JOBS", 2),
        device=os.environ.get("INFERENCE_DEVICE") or None,
    )
