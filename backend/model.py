"""
model.py - degradation classifier: architecture, preprocessing, tiling, and the artifact loader.

This file is used UNCHANGED by both the Colab training notebook and the FastAPI backend, so
class order, input size and preprocessing can never drift apart between training and inference.

Design notes (read these before the demo):
  * The network is a small CNN trained from scratch (~0.3 M parameters). Degradations such as noise and
    blur live in pixel-level detail, so we feed NATIVE-resolution 128x128 tiles. We never resize a
    whole photo down to 224x224 the way an ImageNet classifier would, because that would erase the
    very evidence we are trying to detect.
  * An image is analysed as several tiles; the tile logits are averaged (mean logit) and only then
    passed through a sigmoid. Thresholds are calibrated on exactly this aggregated output.
  * Output is multi-label: one independent sigmoid per class.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Dict, List, Sequence

import numpy as np
import torch
import torch.nn as nn

# --------------------------------------------------------------------------------------
# Constants shared by training and inference. Changing any of them requires retraining.
# --------------------------------------------------------------------------------------
CLASS_NAMES: List[str] = [
    "low_light",
    "low_contrast",
    "gaussian_noise",
    "salt_pepper_noise",
    "blur",
]
NUM_CLASSES = len(CLASS_NAMES)
MODEL_VERSION = "degradation_cnn_v1"
TILE_SIZE = 128            # network input is TILE_SIZE x TILE_SIZE x 3, native resolution
MAX_TILES = 9              # at most a 3x3 grid of tiles per image
ANALYSIS_MAX_SIDE = 768    # images with a longer side are shrunk (INTER_AREA) before analysis
PIXEL_MEAN = 0.5           # preprocessing: x/255, then (x - 0.5) / 0.5  -> range [-1, 1]
PIXEL_STD = 0.5

# File names inside the artifact directory (the notebook writes them, the backend reads them).
WEIGHTS_FILE = "degradation_cnn.pth"
THRESHOLDS_FILE = "class_thresholds.json"
RESTORATION_CONFIG_FILE = "restoration_config.json"
METADATA_FILE = "training_metadata.json"


class ArtifactError(RuntimeError):
    """Raised when model artifacts are missing, corrupt or incompatible with this code."""


# --------------------------------------------------------------------------------------
# Architecture
# --------------------------------------------------------------------------------------
def _conv_bn_relu(c_in: int, c_out: int, stride: int = 1) -> nn.Sequential:
    return nn.Sequential(
        nn.Conv2d(c_in, c_out, 3, stride=stride, padding=1, bias=False),
        nn.BatchNorm2d(c_out),
        nn.ReLU(inplace=True),
    )


class DegradationCNN(nn.Module):
    """Small CNN: a full-resolution stem keeps high-frequency noise/blur cues, later stages downsample."""

    def __init__(self, num_classes: int = NUM_CLASSES, dropout: float = 0.3):
        super().__init__()
        self.features = nn.Sequential(
            _conv_bn_relu(3, 24, 1),      # 128x128, keeps pixel-level detail
            _conv_bn_relu(24, 32, 2),     # 64x64
            _conv_bn_relu(32, 48, 1),
            _conv_bn_relu(48, 48, 2),     # 32x32
            _conv_bn_relu(48, 64, 1),
            _conv_bn_relu(64, 96, 2),     # 16x16
            _conv_bn_relu(96, 96, 1),
            _conv_bn_relu(96, 128, 2),    # 8x8
            _conv_bn_relu(128, 128, 1),
        )
        # average pooling carries global tone statistics, max pooling carries local evidence
        # (e.g. an isolated impulse pixel). Both are concatenated.
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.max_pool = nn.AdaptiveMaxPool2d(1)
        self.head = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(dropout),
            nn.Linear(256, 64),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(64, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        f = self.features(x)
        pooled = torch.cat([self.avg_pool(f), self.max_pool(f)], dim=1)
        return self.head(pooled)  # raw logits; apply sigmoid for probabilities


def count_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters())


# --------------------------------------------------------------------------------------
# Preprocessing and tiling (identical for training-time evaluation and the API)
# --------------------------------------------------------------------------------------
def limit_analysis_size(img_rgb: np.ndarray, max_side: int = ANALYSIS_MAX_SIDE) -> np.ndarray:
    """Shrink very large images (INTER_AREA) so that the analysed scale matches the training scale."""
    import cv2

    h, w = img_rgb.shape[:2]
    longest = max(h, w)
    if longest <= max_side:
        return img_rgb
    scale = max_side / float(longest)
    new_size = (max(1, int(round(w * scale))), max(1, int(round(h * scale))))
    return cv2.resize(img_rgb, new_size, interpolation=cv2.INTER_AREA)


def extract_tiles(img_rgb: np.ndarray, tile: int = TILE_SIZE, max_tiles: int = MAX_TILES) -> np.ndarray:
    """
    Cut an RGB uint8 image (H, W, 3) into native-resolution tiles on an evenly spaced grid.
    Images smaller than a tile are reflect-padded (never resized). Returns (T, tile, tile, 3) uint8.
    """
    if img_rgb.ndim != 3 or img_rgb.shape[2] != 3 or img_rgb.dtype != np.uint8:
        raise ValueError("extract_tiles expects an RGB uint8 array of shape (H, W, 3)")
    h, w = img_rgb.shape[:2]
    pad_h, pad_w = max(0, tile - h), max(0, tile - w)
    if pad_h or pad_w:
        img_rgb = np.pad(img_rgb, ((0, pad_h), (0, pad_w), (0, 0)), mode="reflect")
        h, w = img_rgb.shape[:2]
    grid = int(math.isqrt(max_tiles))
    ny = max(1, min(grid, math.ceil(h / tile)))
    nx = max(1, min(grid, math.ceil(w / tile)))
    ys = np.linspace(0, h - tile, ny).round().astype(int)
    xs = np.linspace(0, w - tile, nx).round().astype(int)
    return np.stack([img_rgb[y:y + tile, x:x + tile] for y in ys for x in xs], axis=0)


def to_model_input(batch_uint8_nhwc: torch.Tensor) -> torch.Tensor:
    """(B, H, W, 3) uint8 tensor (any device) -> (B, 3, H, W) float32 in [-1, 1]. Used by training AND inference."""
    x = batch_uint8_nhwc.permute(0, 3, 1, 2).float() / 255.0
    return (x - PIXEL_MEAN) / PIXEL_STD


def tiles_to_tensor(tiles_uint8: np.ndarray) -> torch.Tensor:
    """(T, H, W, 3) uint8 numpy array -> model input tensor."""
    return to_model_input(torch.from_numpy(np.ascontiguousarray(tiles_uint8)))


def aggregate_tile_logits(tile_logits: torch.Tensor) -> torch.Tensor:
    """(T, C) -> (C,): mean logit over the tiles of one image."""
    return tile_logits.mean(dim=0)


# --------------------------------------------------------------------------------------
# Artifact loading + prediction
# --------------------------------------------------------------------------------------
def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _read_json(path: Path) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError as exc:
        raise ArtifactError(f"Required artifact is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ArtifactError(f"Artifact is not valid JSON: {path} ({exc})") from exc


def validate_thresholds(data: dict) -> Dict[str, float]:
    """Return {class_name: threshold} in CLASS_NAMES order or raise ArtifactError."""
    if data.get("class_names") != CLASS_NAMES:
        raise ArtifactError(
            f"class_thresholds.json class order {data.get('class_names')} does not match code {CLASS_NAMES}."
        )
    th = data.get("thresholds")
    if not isinstance(th, dict) or set(th) != set(CLASS_NAMES):
        raise ArtifactError("class_thresholds.json must contain a 'thresholds' entry for every class.")
    out = {}
    for name in CLASS_NAMES:
        value = th[name]
        if not isinstance(value, (int, float)) or not (0.0 < float(value) < 1.0):
            raise ArtifactError(f"Threshold for '{name}' must be a number in (0, 1), got {value!r}.")
        out[name] = float(value)
    return out


class DegradationPredictor:
    """Loads the trained CNN once and turns an RGB image into per-class probabilities + decisions."""

    def __init__(self, artifact_dir: Path, device: str | None = None):
        artifact_dir = Path(artifact_dir)
        weights_path = artifact_dir / WEIGHTS_FILE
        if not weights_path.is_file():
            raise ArtifactError(
                f"Model weights not found: {weights_path}. Train the model with the Colab notebook and copy "
                f"the files from deployment_artifacts.zip into {artifact_dir}."
            )
        metadata = _read_json(artifact_dir / METADATA_FILE)
        self.thresholds = validate_thresholds(_read_json(artifact_dir / THRESHOLDS_FILE))

        # ---- compatibility checks between artifacts and this code ----
        problems = []
        if metadata.get("class_names") != CLASS_NAMES:
            problems.append(f"class order {metadata.get('class_names')} != {CLASS_NAMES}")
        if metadata.get("model_version") != MODEL_VERSION:
            problems.append(f"model_version {metadata.get('model_version')} != {MODEL_VERSION}")
        if metadata.get("tile_size") != TILE_SIZE:
            problems.append(f"tile_size {metadata.get('tile_size')} != {TILE_SIZE}")
        pre = metadata.get("preprocessing", {})
        if pre.get("mean") != PIXEL_MEAN or pre.get("std") != PIXEL_STD:
            problems.append("preprocessing mean/std differ from this code")
        if problems:
            raise ArtifactError("Artifacts are incompatible with this backend: " + "; ".join(problems))
        expected_hash = metadata.get("weights_sha256")
        if expected_hash and expected_hash != file_sha256(weights_path):
            raise ArtifactError("degradation_cnn.pth does not match the hash stored in training_metadata.json.")

        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
        self.model = DegradationCNN()
        try:
            state = torch.load(weights_path, map_location="cpu", weights_only=True)
            self.model.load_state_dict(state)
        except Exception as exc:  # corrupt file or architecture mismatch
            raise ArtifactError(f"Could not load weights from {weights_path}: {exc}") from exc
        self.model.to(self.device).eval()
        self.metadata = metadata

    @torch.inference_mode()
    def logits_for_image(self, img_rgb: np.ndarray) -> np.ndarray:
        """Aggregated logits (C,) for a full RGB uint8 image."""
        tiles = extract_tiles(limit_analysis_size(img_rgb))
        x = tiles_to_tensor(tiles).to(self.device)
        return aggregate_tile_logits(self.model(x)).cpu().numpy()

    def predict(self, img_rgb: np.ndarray) -> Dict[str, Dict[str, float | bool]]:
        """Per-class {'probability', 'threshold', 'detected'} using the calibrated thresholds."""
        logits = self.logits_for_image(img_rgb)
        probs = 1.0 / (1.0 + np.exp(-logits.astype(np.float64)))
        return {
            name: {
                "probability": float(probs[i]),
                "threshold": self.thresholds[name],
                "detected": bool(probs[i] >= self.thresholds[name]),
            }
            for i, name in enumerate(CLASS_NAMES)
        }


def apply_thresholds(probabilities: Sequence[float], thresholds: Dict[str, float]) -> List[bool]:
    """Pure helper (also unit-tested): probability >= class threshold."""
    return [bool(p >= thresholds[name]) for p, name in zip(probabilities, CLASS_NAMES)]
