"""
degradations.py - synthetic degradation generators with known labels.

Used by the Colab notebook (training / validation / test data), the unit tests and the
evaluation tooling. All functions take and return RGB uint8 arrays (H, W, 3).

Realistic order of operations (mimics a camera): tonal damage -> optical blur -> sensor noise ->
impulse noise. Each degradation is drawn from a severity range ("mild", "moderate", "severe").
"""
from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

import cv2
import numpy as np

from model import CLASS_NAMES

SEVERITY_LEVELS = ("mild", "moderate", "severe")

# Parameter ranges per degradation and severity. These ranges define what the labels MEAN, so they
# are recorded in training_metadata.json by the notebook.
SEVERITY_RANGES: Dict[str, Dict[str, Dict[str, Tuple[float, float]]]] = {
    "low_light": {   # out = gain * x^gamma
        "mild": {"gamma": (1.6, 2.2), "gain": (0.75, 1.0)},
        "moderate": {"gamma": (2.2, 3.0), "gain": (0.55, 0.85)},
        "severe": {"gamma": (3.0, 4.2), "gain": (0.35, 0.7)},
    },
    "low_contrast": {  # out = 0.5 + shift + alpha * (x - 0.5)
        "mild": {"alpha": (0.55, 0.7), "shift": (-0.05, 0.05)},
        "moderate": {"alpha": (0.35, 0.55), "shift": (-0.08, 0.08)},
        "severe": {"alpha": (0.18, 0.35), "shift": (-0.1, 0.1)},
    },
    "gaussian_noise": {  # sigma on the 0..255 scale
        "mild": {"sigma": (5.0, 12.0)},
        "moderate": {"sigma": (12.0, 25.0)},
        "severe": {"sigma": (25.0, 45.0)},
    },
    "salt_pepper_noise": {  # fraction of corrupted pixels
        "mild": {"amount": (0.005, 0.02)},
        "moderate": {"amount": (0.02, 0.06)},
        "severe": {"amount": (0.06, 0.15)},
    },
    "blur": {  # gaussian (defocus-like) or linear motion blur
        "mild": {"sigma": (1.0, 1.8), "length": (5, 9)},
        "moderate": {"sigma": (1.8, 3.0), "length": (9, 15)},
        "severe": {"sigma": (3.0, 5.0), "length": (15, 27)},
    },
}

# Probability of drawing 0, 1, 2, 3 simultaneous degradations (index = count).
DEFAULT_COUNT_PROBS = (0.15, 0.40, 0.30, 0.15)


def _u(rng: np.random.Generator, lo_hi: Tuple[float, float]) -> float:
    return float(rng.uniform(lo_hi[0], lo_hi[1]))


def apply_low_light(img: np.ndarray, gamma: float, gain: float) -> np.ndarray:
    x = img.astype(np.float32) / 255.0
    return np.clip(255.0 * gain * np.power(x, gamma), 0, 255).astype(np.uint8)


def apply_low_contrast(img: np.ndarray, alpha: float, shift: float) -> np.ndarray:
    x = img.astype(np.float32) / 255.0
    return np.clip(255.0 * (0.5 + shift + alpha * (x - 0.5)), 0, 255).astype(np.uint8)


def apply_gaussian_noise(img: np.ndarray, sigma: float, rng: np.random.Generator) -> np.ndarray:
    noise = rng.normal(0.0, sigma, img.shape).astype(np.float32)
    return np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)


def apply_salt_pepper(img: np.ndarray, amount: float, rng: np.random.Generator) -> np.ndarray:
    out = img.copy()
    h, w = img.shape[:2]
    corrupted = rng.random((h, w)) < amount
    salt = rng.random((h, w)) < 0.5
    out[corrupted & salt] = 255
    out[corrupted & ~salt] = 0
    return out


def motion_kernel(length: int, angle_deg: float) -> np.ndarray:
    length = max(3, int(length) | 1)  # odd, >= 3
    k = np.zeros((length, length), np.float32)
    k[length // 2, :] = 1.0
    rot = cv2.getRotationMatrix2D((length / 2 - 0.5, length / 2 - 0.5), angle_deg, 1.0)
    k = cv2.warpAffine(k, rot, (length, length))
    s = k.sum()
    return k / s if s > 0 else np.pad(np.ones((1, 1), np.float32), length // 2)


def apply_blur(img: np.ndarray, kind: str, sigma: float, length: int, angle: float) -> np.ndarray:
    if kind == "gaussian":
        return cv2.GaussianBlur(img, (0, 0), sigmaX=sigma, borderType=cv2.BORDER_REFLECT_101)
    return cv2.filter2D(img, -1, motion_kernel(length, angle), borderType=cv2.BORDER_REFLECT_101)


def sample_label_set(
    rng: np.random.Generator,
    count_probs: Sequence[float] = DEFAULT_COUNT_PROBS,
) -> List[str]:
    """Choose which degradations a synthetic sample receives (possibly none = a clean example)."""
    p = np.asarray(count_probs, dtype=np.float64)
    count = int(rng.choice(len(p), p=p / p.sum()))
    if count == 0:
        return []
    chosen = rng.choice(len(CLASS_NAMES), size=count, replace=False)
    return [CLASS_NAMES[i] for i in sorted(chosen)]


def degrade(
    img: np.ndarray,
    rng: np.random.Generator,
    labels: Sequence[str] | None = None,
    severities: Sequence[str] = SEVERITY_LEVELS,
    count_probs: Sequence[float] = DEFAULT_COUNT_PROBS,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, dict]]:
    """
    Degrade a CLEAN image. Returns (degraded_uint8, label_vector float32[5], applied_params).
    `labels` forces the degradation set (used for tests); otherwise it is sampled.
    """
    chosen = list(labels) if labels is not None else sample_label_set(rng, count_probs)
    unknown = set(chosen) - set(CLASS_NAMES)
    if unknown:
        raise ValueError(f"Unknown degradation(s): {sorted(unknown)}")
    params: Dict[str, dict] = {}
    out = img
    if "low_light" in chosen:
        sev = str(rng.choice(list(severities)))
        r = SEVERITY_RANGES["low_light"][sev]
        params["low_light"] = {"severity": sev, "gamma": _u(rng, r["gamma"]), "gain": _u(rng, r["gain"])}
        out = apply_low_light(out, params["low_light"]["gamma"], params["low_light"]["gain"])
    if "low_contrast" in chosen:
        sev = str(rng.choice(list(severities)))
        r = SEVERITY_RANGES["low_contrast"][sev]
        params["low_contrast"] = {"severity": sev, "alpha": _u(rng, r["alpha"]), "shift": _u(rng, r["shift"])}
        out = apply_low_contrast(out, params["low_contrast"]["alpha"], params["low_contrast"]["shift"])
    if "blur" in chosen:
        sev = str(rng.choice(list(severities)))
        r = SEVERITY_RANGES["blur"][sev]
        kind = "gaussian" if rng.random() < 0.5 else "motion"
        params["blur"] = {
            "severity": sev, "kind": kind, "sigma": _u(rng, r["sigma"]),
            "length": int(round(_u(rng, r["length"]))), "angle": float(rng.uniform(0, 180)),
        }
        out = apply_blur(out, kind, params["blur"]["sigma"], params["blur"]["length"], params["blur"]["angle"])
    if "gaussian_noise" in chosen:
        sev = str(rng.choice(list(severities)))
        params["gaussian_noise"] = {"severity": sev, "sigma": _u(rng, SEVERITY_RANGES["gaussian_noise"][sev]["sigma"])}
        out = apply_gaussian_noise(out, params["gaussian_noise"]["sigma"], rng)
    if "salt_pepper_noise" in chosen:
        sev = str(rng.choice(list(severities)))
        params["salt_pepper_noise"] = {"severity": sev, "amount": _u(rng, SEVERITY_RANGES["salt_pepper_noise"][sev]["amount"])}
        out = apply_salt_pepper(out, params["salt_pepper_noise"]["amount"], rng)
    target = np.array([1.0 if n in chosen else 0.0 for n in CLASS_NAMES], dtype=np.float32)
    return out, target, params
