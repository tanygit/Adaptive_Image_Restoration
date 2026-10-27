"""
image_io.py - safe upload decoding.

Validation uses the DECODED format (Pillow inspects the bytes), never the file extension or the
client-supplied Content-Type. Dimensions are checked from the header BEFORE the pixels are decoded, so a
small file that claims to be enormous cannot exhaust memory.
"""
from __future__ import annotations

import io
import re
from typing import List, Tuple

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


class ImageValidationError(Exception):
    """A client-side problem with the uploaded file; carries an HTTP status and a stable error code."""

    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def sanitize_filename(name: str | None) -> str:
    """Display-only: strip any directory part and unusual characters. Never used to build a disk path."""
    base = re.split(r"[\\/]", name or "")[-1]
    base = re.sub(r"[^A-Za-z0-9._ -]", "_", base).strip(" .")
    return base[:100] or "upload"


def decode_image(data: bytes, max_side: int, min_side: int, max_pixels: int) -> Tuple[np.ndarray, List[str], str]:
    """Return (RGB uint8 array, warnings, detected format) or raise ImageValidationError."""
    if not data:
        raise ImageValidationError(400, "empty_file", "The uploaded file is empty.")
    warnings: List[str] = []
    try:
        img = Image.open(io.BytesIO(data))
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError) as exc:
        raise ImageValidationError(415, "unsupported_or_corrupt_image",
                                   "The file is not a readable JPEG, PNG or WebP image.") from exc
    fmt = (img.format or "").upper()
    if fmt not in ALLOWED_FORMATS:
        raise ImageValidationError(415, "unsupported_format",
                                   f"Unsupported image format '{fmt or 'unknown'}'. Allowed: JPEG, PNG, WebP.")
    width, height = img.size
    if min(width, height) < min_side:
        raise ImageValidationError(422, "image_too_small", f"Image is {width}x{height}; the minimum side is {min_side}px.")
    if max(width, height) > max_side:
        raise ImageValidationError(422, "image_too_large_dimensions",
                                   f"Image is {width}x{height}; the maximum side is {max_side}px.")
    if width * height > max_pixels:
        raise ImageValidationError(422, "image_too_many_pixels",
                                   f"Image has {width * height:,} pixels; the maximum is {max_pixels:,}.")
    if getattr(img, "n_frames", 1) > 1:
        warnings.append("Animated image: only the first frame was processed.")
    try:
        img.load()  # full decode; truncated or corrupt data raises here
    except (OSError, SyntaxError, ValueError, Image.DecompressionBombError) as exc:
        raise ImageValidationError(422, "corrupt_image", "The image data is corrupt or truncated.") from exc

    try:
        transposed = ImageOps.exif_transpose(img)
        if transposed is not None and transposed.size != img.size:
            warnings.append("EXIF orientation was applied to the image.")
        img = transposed if transposed is not None else img
    except Exception:  # damaged EXIF must not reject an otherwise valid image
        warnings.append("EXIF orientation data could not be read and was ignored.")

    mode = img.mode
    if mode in ("RGBA", "LA") or (mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        img = Image.alpha_composite(background, rgba).convert("RGB")
        warnings.append("Transparency was composited onto a white background.")
    elif mode.startswith("I") or mode == "F":
        arr = np.asarray(img).astype(np.float64)
        arr = arr / 257.0 if arr.max() > 255 else arr
        img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGB")
        warnings.append("High-bit-depth image was converted to 8 bits per channel.")
    else:
        img = img.convert("RGB")
    return np.ascontiguousarray(np.asarray(img, dtype=np.uint8)), warnings, fmt
