"""
restoration.py - classical (OpenCV) restoration operations and the adaptive pipeline.

The neural network only DETECTS degradations. Restoration is done with transparent classical operations:

  salt_pepper_noise -> selective median filter (only pixels that disagree strongly with their neighbourhood)
  low_light         -> controlled gamma on the Lab lightness channel (never brightens past a target mean)
  gaussian_noise    -> OpenCV non-local-means, strength derived from an estimated noise sigma
  low_contrast      -> percentile stretch + CLAHE on Lab lightness, blended with the original
  blur              -> conservative, halo-limited unsharp mask on lightness (NOT deblurring, see below)

Default order (configurable): impulse noise -> low light -> Gaussian noise -> low contrast -> blur
  * impulses first: any smoothing filter would smear them into blotches;
  * brighten before denoising: brightening amplifies noise, so the denoiser must see the final noise level;
  * denoise before CLAHE and sharpening: both of those amplify noise;
  * sharpen last: it works on the final tone/noise state.

Blur limitation: the blur kernel is unknown for an uploaded photo. Blind deconvolution with a guessed kernel
(e.g. Richardson-Lucy) creates ringing and noise, and sharpening cannot recover information that was lost.
We therefore apply only a mild unsharp mask and say so in the response.
"""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Mapping, Optional, Tuple

import cv2
import numpy as np

from image_quality import estimate_impulse_fraction, estimate_noise_sigma

STRENGTHS = ("gentle", "balanced", "strong")
OPERATION_NAMES = ("salt_pepper_noise", "low_light", "gaussian_noise", "low_contrast", "blur")


# --------------------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------------------
def default_config() -> dict:
    """Default settings; the notebook writes this to restoration_config.json, users may edit that file."""
    return {
        "config_version": 1,
        "default_strength": "balanced",
        "operation_order": list(OPERATION_NAMES),
        "strengths": {
            "gentle": {
                "salt_pepper_noise": {"diff_threshold": 70},
                "low_light": {"target_lightness": 100, "min_gamma": 0.65},
                "gaussian_noise": {"h_factor": 0.35, "h_min": 1.5, "h_max": 8.0},
                "low_contrast": {"clahe_clip": 1.5, "stretch_span": 150, "stretch_max_gain": 2.0, "blend": 0.6},
                "blur": {"amount": 0.5, "threshold": 4.0},
            },
            "balanced": {
                "salt_pepper_noise": {"diff_threshold": 50},
                "low_light": {"target_lightness": 118, "min_gamma": 0.5},
                "gaussian_noise": {"h_factor": 0.5, "h_min": 2.0, "h_max": 14.0},
                "low_contrast": {"clahe_clip": 2.5, "stretch_span": 185, "stretch_max_gain": 3.0, "blend": 0.8},
                "blur": {"amount": 0.9, "threshold": 3.0},
            },
            "strong": {
                "salt_pepper_noise": {"diff_threshold": 35},
                "low_light": {"target_lightness": 135, "min_gamma": 0.4},
                "gaussian_noise": {"h_factor": 0.7, "h_min": 3.0, "h_max": 20.0},
                "low_contrast": {"clahe_clip": 3.5, "stretch_span": 210, "stretch_max_gain": 4.5, "blend": 1.0},
                "blur": {"amount": 1.4, "threshold": 2.0},
            },
        },
        # Sanity guards. They only SKIP an operation when the measured statistic clearly contradicts the
        # classifier, and every skip is reported in the response. They never add operations.
        "guards": {
            "low_light_skip_if_lightness_above": 150,
            "low_contrast_skip_if_range_above": 215,
            "gaussian_noise_skip_if_sigma_below": 1.0,
            "median_5x5_if_impulse_fraction_above": 0.04,
            "nlm_fast_mode_above_pixels": 3_000_000,
        },
    }


def validate_config(cfg: dict) -> dict:
    """Raise ValueError if the config is incomplete; returns cfg."""
    base = default_config()
    if cfg.get("default_strength") not in STRENGTHS:
        raise ValueError(f"default_strength must be one of {STRENGTHS}")
    order = cfg.get("operation_order")
    if not isinstance(order, list) or sorted(order) != sorted(OPERATION_NAMES):
        raise ValueError(f"operation_order must be a permutation of {list(OPERATION_NAMES)}")
    for strength in STRENGTHS:
        for op, params in base["strengths"][strength].items():
            have = cfg.get("strengths", {}).get(strength, {}).get(op)
            if not isinstance(have, dict) or not set(params) <= set(have):
                raise ValueError(f"strengths.{strength}.{op} must define {sorted(params)}")
    for key in base["guards"]:
        if key not in cfg.get("guards", {}):
            raise ValueError(f"guards.{key} is missing")
    return cfg


def load_config(path: Optional[Path]) -> dict:
    """Load and validate restoration_config.json; fall back to defaults when the file does not exist."""
    if path is None or not Path(path).is_file():
        return default_config()
    with open(path, "r", encoding="utf-8") as fh:
        return validate_config(json.load(fh))


# --------------------------------------------------------------------------------------
# Individual operations. Each returns (image, parameters_used, human_readable_notes).
# --------------------------------------------------------------------------------------
def _lab_split(img_rgb: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    lab = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2LAB)
    return lab[..., 0].copy(), lab


def _lab_merge(lightness: np.ndarray, lab: np.ndarray) -> np.ndarray:
    out = lab.copy()
    out[..., 0] = np.clip(lightness, 0, 255).astype(np.uint8)
    return cv2.cvtColor(out, cv2.COLOR_LAB2RGB)


def remove_impulse_noise(img: np.ndarray, p: dict, guards: dict) -> Tuple[np.ndarray, dict]:
    """Selective median: only pixels far from the local median are replaced, so detail is kept elsewhere."""
    fraction = estimate_impulse_fraction(img)
    ksize = 5 if fraction > guards["median_5x5_if_impulse_fraction_above"] else 3
    med = cv2.medianBlur(img, ksize)
    diff = np.abs(img.astype(np.int16) - med.astype(np.int16)).max(axis=2)
    mask = diff > p["diff_threshold"]
    out = img.copy()
    out[mask] = med[mask]
    return out, {"median_kernel": ksize, "diff_threshold": p["diff_threshold"],
                 "estimated_impulse_fraction": round(fraction, 4), "pixels_replaced_fraction": round(float(mask.mean()), 4)}


def brighten_low_light(img: np.ndarray, p: dict) -> Tuple[np.ndarray, dict]:
    """Gamma on Lab lightness chosen so the mean lightness moves toward a target, never past it."""
    lightness, lab = _lab_split(img)
    mean_l = float(lightness.mean())
    mean_n, target_n = max(mean_l, 1.0) / 255.0, p["target_lightness"] / 255.0
    if mean_n >= target_n:
        return img, {"applied": False, "mean_lightness": round(mean_l, 1), "target_lightness": p["target_lightness"]}
    gamma = float(np.clip(np.log(target_n) / np.log(mean_n), p["min_gamma"], 1.0))
    lut = (255.0 * np.power(np.arange(256) / 255.0, gamma)).clip(0, 255).astype(np.uint8)
    return _lab_merge(cv2.LUT(lightness, lut), lab), {
        "applied": True, "gamma": round(gamma, 3), "mean_lightness_before": round(mean_l, 1),
        "target_lightness": p["target_lightness"]}


def denoise_gaussian(img: np.ndarray, p: dict, guards: dict, force: bool = False) -> Tuple[np.ndarray, dict]:
    """Non-local means; filter strength h follows the estimated sigma, clipped to [h_min, h_max]."""
    sigma = estimate_noise_sigma(img)
    if sigma < guards["gaussian_noise_skip_if_sigma_below"] and not force:
        return img, {"applied": False, "estimated_sigma": round(sigma, 2)}
    h = float(np.clip(p["h_factor"] * sigma, p["h_min"], p["h_max"]))
    fast = img.shape[0] * img.shape[1] > guards["nlm_fast_mode_above_pixels"]
    template, search = (5, 11) if fast else (7, 21)
    bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    out = cv2.fastNlMeansDenoisingColored(bgr, None, h, h, template, search)
    return cv2.cvtColor(out, cv2.COLOR_BGR2RGB), {
        "applied": True, "estimated_sigma": round(sigma, 2), "h": round(h, 2),
        "template_window": template, "search_window": search, "fast_mode": bool(fast)}


def enhance_contrast(img: np.ndarray, p: dict) -> Tuple[np.ndarray, dict]:
    """Percentile stretch (only if the tonal span is narrow) + CLAHE on lightness, blended with the original."""
    lightness, lab = _lab_split(img)
    original = lightness.astype(np.float32)
    work = original.copy()
    lo, hi = np.percentile(work, [1, 99])
    span = float(hi - lo)
    gain = 1.0
    if span > 1.0 and span < p["stretch_span"]:
        gain = float(min(p["stretch_span"] / span, p["stretch_max_gain"]))
        centre = (lo + hi) / 2.0
        work = np.clip(centre + (work - centre) * gain, 0, 255)
    clahe = cv2.createCLAHE(clipLimit=p["clahe_clip"], tileGridSize=(8, 8))
    work = clahe.apply(work.astype(np.uint8)).astype(np.float32)
    out_l = p["blend"] * work + (1.0 - p["blend"]) * original
    return _lab_merge(out_l, lab), {"stretch_gain": round(gain, 2), "clahe_clip": p["clahe_clip"], "blend": p["blend"],
                                   "tonal_span_before": round(span, 1)}


def sharpen_conservative(img: np.ndarray, p: dict, noise_present: bool) -> Tuple[np.ndarray, dict]:
    """Halo-limited unsharp mask on lightness. Radius scales with image size; amount is reduced if noisy."""
    lightness, lab = _lab_split(img)
    l32 = lightness.astype(np.float32)
    sigma = max(0.8, 0.0015 * max(img.shape[:2]))
    detail = l32 - cv2.GaussianBlur(l32, (0, 0), sigma)
    thr = p["threshold"]
    soft = np.clip((np.abs(detail) - thr) / max(thr, 1e-6), 0.0, 1.0)  # ignore tiny variations (noise)
    amount = p["amount"] * (0.5 if noise_present else 1.0)
    out = l32 + amount * detail * soft
    out = np.clip(out, cv2.erode(lightness, np.ones((3, 3), np.uint8)), cv2.dilate(lightness, np.ones((3, 3), np.uint8)))
    return _lab_merge(out, lab), {"unsharp_sigma_px": round(sigma, 2), "amount": round(amount, 2), "threshold": thr}


# --------------------------------------------------------------------------------------
# Adaptive pipeline
# --------------------------------------------------------------------------------------
@dataclass
class RestorationResult:
    image: np.ndarray
    operations: List[dict] = field(default_factory=list)   # applied operations with reasons
    skipped: List[dict] = field(default_factory=list)      # operations considered but not applied (with reasons)
    warnings: List[str] = field(default_factory=list)


class Restorer:
    def __init__(self, config: Optional[dict] = None):
        self.config = validate_config(copy.deepcopy(config) if config else default_config())

    @property
    def default_strength(self) -> str:
        return self.config["default_strength"]

    def restore(self, img_rgb: np.ndarray, detected: Mapping[str, bool], strength: Optional[str] = None,
                use_guards: bool = True) -> RestorationResult:
        """Apply the operations for every class with detected[class] == True, in the configured order."""
        strength = strength or self.default_strength
        if strength not in STRENGTHS:
            raise ValueError(f"strength must be one of {STRENGTHS}, got {strength!r}")
        if img_rgb.ndim != 3 or img_rgb.shape[2] != 3 or img_rgb.dtype != np.uint8:
            raise ValueError("restore expects an RGB uint8 array of shape (H, W, 3)")
        params, guards = self.config["strengths"][strength], self.config["guards"]
        result = RestorationResult(image=img_rgb.copy())

        for name in self.config["operation_order"]:
            if not detected.get(name, False):
                continue
            img = result.image
            if name == "salt_pepper_noise":
                out, info = remove_impulse_noise(img, params[name], guards)
                self._add(result, "selective_median_filter", name, info, out,
                          "Classifier detected impulse (salt-and-pepper) noise; isolated outlier pixels are replaced by the "
                          f"local {info['median_kernel']}x{info['median_kernel']} median, other pixels are left untouched.")
            elif name == "low_light":
                lightness = float(cv2.cvtColor(img, cv2.COLOR_RGB2LAB)[..., 0].mean())
                if use_guards and lightness > guards["low_light_skip_if_lightness_above"]:
                    self._skip(result, name, f"Classifier flagged low light but measured mean lightness is {lightness:.0f}/255 "
                               "(already bright); skipped to avoid over-exposure.")
                    continue
                out, info = brighten_low_light(img, params[name])
                if not info["applied"]:
                    self._skip(result, name, f"Mean lightness {info['mean_lightness']} already reaches the "
                               f"'{strength}' target {info['target_lightness']}; no brightening needed.")
                    continue
                self._add(result, "gamma_correction_lightness", name, info, out,
                          "Classifier detected low light; gamma < 1 on the Lab lightness channel lifts shadows toward the "
                          f"'{strength}' target brightness without exceeding it.")
            elif name == "gaussian_noise":
                out, info = denoise_gaussian(img, params[name], guards, force=not use_guards)
                if not info["applied"]:
                    self._skip(result, name, f"Classifier flagged Gaussian noise but the estimated noise sigma is only "
                               f"{info['estimated_sigma']}; skipped to avoid needless smoothing.")
                    continue
                if info["fast_mode"]:
                    result.warnings.append("Large image: faster, smaller non-local-means windows were used.")
                self._add(result, "non_local_means_denoise", name, info, out,
                          f"Classifier detected Gaussian noise; non-local means with strength h={info['h']} "
                          f"derived from the estimated noise sigma {info['estimated_sigma']}.")
            elif name == "low_contrast":
                rng_before = float(np.subtract(*np.percentile(cv2.cvtColor(img, cv2.COLOR_RGB2GRAY), [95, 5])))
                if use_guards and rng_before > guards["low_contrast_skip_if_range_above"]:
                    self._skip(result, name, f"Classifier flagged low contrast but the measured 5-95% luminance range is "
                               f"{rng_before:.0f}/255 (already wide); skipped.")
                    continue
                out, info = enhance_contrast(img, params[name])
                self._add(result, "stretch_plus_clahe_lightness", name, info, out,
                          "Classifier detected low contrast; percentile stretch (if the tonal span is narrow) and CLAHE on "
                          "the lightness channel only, blended with the original to avoid halos and colour shifts.")
            elif name == "blur":
                noisy = bool(detected.get("gaussian_noise", False) or detected.get("salt_pepper_noise", False))
                out, info = sharpen_conservative(img, params[name], noisy)
                self._add(result, "conservative_unsharp_mask", name, info, out,
                          "Classifier detected blur; only a mild, halo-limited unsharp mask is applied because the blur kernel "
                          "is unknown.")
                result.warnings.append(
                    "Blur: this is NOT deblurring. Sharpening raises edge contrast but cannot recover detail that the blur "
                    "removed; strongly blurred images will stay blurry.")
        return result

    @staticmethod
    def _add(result: RestorationResult, op: str, cls: str, info: dict, image: np.ndarray, reason: str) -> None:
        result.image = image
        result.operations.append({"operation": op, "degradation": cls, "parameters": info, "reason": reason})

    @staticmethod
    def _skip(result: RestorationResult, cls: str, reason: str) -> None:
        result.skipped.append({"degradation": cls, "reason": reason})
        result.warnings.append(reason)

    def restore_fixed_baseline(self, img_rgb: np.ndarray, strength: Optional[str] = None) -> RestorationResult:
        """Non-adaptive baseline for evaluation: every operation on every image, no guards, no classifier."""
        return self.restore(img_rgb, {name: True for name in OPERATION_NAMES}, strength, use_guards=False)
