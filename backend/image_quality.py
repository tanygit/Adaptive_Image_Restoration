"""
image_quality.py - simple, explainable image statistics.

IMPORTANT: these are heuristics, not perceptual-quality scores. They describe pixel statistics of ONE image
and have no universal "good/bad" threshold (a foggy landscape and a studio portrait have very different
natural contrast; a smooth sky has a low Laplacian variance without being blurry). They are used to
(a) scale restoration strength and (b) report before/after numbers - never as proof of better quality.
"""
from __future__ import annotations

from typing import Dict

import cv2
import numpy as np

STATS_MAX_SIDE = 512  # sharpness statistics are computed on a size-normalised copy
# Luminance mixes three channels (0.299 R + 0.587 G + 0.114 B). If the noise is independent per channel, the
# luminance noise std is only 0.67x the per-channel std, so the estimate is divided by this factor.
GRAY_NOISE_FACTOR = float(np.sqrt(0.299**2 + 0.587**2 + 0.114**2))


def _to_gray(img_rgb: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)


def _normalised_gray(img_rgb: np.ndarray) -> np.ndarray:
    gray = _to_gray(img_rgb)
    longest = max(gray.shape)
    if longest > STATS_MAX_SIDE:
        s = STATS_MAX_SIDE / longest
        gray = cv2.resize(gray, (max(1, round(gray.shape[1] * s)), max(1, round(gray.shape[0] * s))),
                          interpolation=cv2.INTER_AREA)
    return gray


def estimate_noise_sigma(img_rgb: np.ndarray) -> float:
    """
    Robust Immerkaer-style noise estimate (sigma on the 0..255 scale), computed on the ORIGINAL pixel grid.
    Per-block estimates are computed and a low percentile is used, so textured blocks do not dominate.
    Impulse noise inflates only some blocks, which the low percentile also tolerates. Heuristic only.
    """
    gray = _to_gray(img_rgb).astype(np.float32)
    if min(gray.shape) < 8:
        return 0.0
    kernel = np.array([[1, -2, 1], [-2, 4, -2], [1, -2, 1]], dtype=np.float32)
    resp = np.abs(cv2.filter2D(gray, -1, kernel, borderType=cv2.BORDER_REFLECT_101))[1:-1, 1:-1]
    bs = 32
    hb, wb = resp.shape[0] // bs, resp.shape[1] // bs
    if hb == 0 or wb == 0:
        return float(np.sqrt(np.pi / 2.0) / 6.0 * resp.mean()) / GRAY_NOISE_FACTOR
    blocks = resp[: hb * bs, : wb * bs].reshape(hb, bs, wb, bs).mean(axis=(1, 3)).ravel()
    return float(np.sqrt(np.pi / 2.0) / 6.0 * np.percentile(blocks, 25)) / GRAY_NOISE_FACTOR


def estimate_impulse_fraction(img_rgb: np.ndarray, diff_threshold: float = 80.0) -> float:
    """Fraction of pixels that differ from their 3x3 median by more than diff_threshold (gray levels)."""
    gray = _to_gray(img_rgb)
    if min(gray.shape) < 3:
        return 0.0
    med = cv2.medianBlur(gray, 3)
    return float(np.mean(np.abs(gray.astype(np.int16) - med.astype(np.int16)) > diff_threshold))


def compute_quality_stats(img_rgb: np.ndarray) -> Dict[str, float]:
    """Return JSON-serialisable statistics for an RGB uint8 image."""
    if img_rgb.ndim != 3 or img_rgb.shape[2] != 3 or img_rgb.dtype != np.uint8:
        raise ValueError("compute_quality_stats expects an RGB uint8 array of shape (H, W, 3)")
    h, w = img_rgb.shape[:2]
    gray = _to_gray(img_rgb)
    p5, p95 = np.percentile(gray, [5, 95])
    norm = _normalised_gray(img_rgb)
    lap_var = float(cv2.Laplacian(norm, cv2.CV_64F).var())
    gray_var = float(norm.astype(np.float64).var())
    return {
        "width": int(w),
        "height": int(h),
        "megapixels": round(w * h / 1e6, 3),
        "mean_luminance": round(float(gray.mean()), 2),          # 0..255
        "contrast_std": round(float(gray.std()), 2),             # std of luminance, 0..~128
        "dynamic_range_p5_p95": round(float(p95 - p5), 2),       # robust tonal spread, 0..255
        "laplacian_variance": round(lap_var, 2),                 # size-normalised (long side <= 512)
        "sharpness_relative": round(lap_var / (gray_var + 1.0), 4),  # Laplacian variance / luminance variance
        "noise_sigma_estimate": round(estimate_noise_sigma(img_rgb), 2),
        "impulse_pixel_fraction": round(estimate_impulse_fraction(img_rgb), 5),
    }


STATS_DISCLAIMER = (
    "Statistics are simple heuristics computed from this image alone. They are not perceptual quality scores, "
    "and a change in a statistic does not by itself prove the image looks better."
)
