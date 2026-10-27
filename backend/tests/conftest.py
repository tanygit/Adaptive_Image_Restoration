"""
Shared test fixtures.

IMPORTANT: the model artifacts created here use RANDOMLY INITIALISED weights. They exist only so that the
plumbing (loading, thresholds, API, restoration) can be tested without a trained model. They are written to a
temporary folder, are never shipped, and say nothing about detection accuracy.
"""
import io
import json
import sys
from dataclasses import replace
from pathlib import Path

import cv2
import numpy as np
import pytest
import torch
from fastapi.testclient import TestClient
from PIL import Image

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import model as M  # noqa: E402
from config import Settings  # noqa: E402
from main import create_app  # noqa: E402
from restoration import default_config  # noqa: E402

TEST_THRESHOLDS = {"low_light": 0.30, "low_contrast": 0.40, "gaussian_noise": 0.50, "salt_pepper_noise": 0.60, "blur": 0.70}


def write_artifacts(directory: Path, thresholds=None, class_names=None) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    torch.manual_seed(0)
    net = M.DegradationCNN()
    torch.save(net.state_dict(), directory / M.WEIGHTS_FILE)
    (directory / M.THRESHOLDS_FILE).write_text(json.dumps(
        {"class_names": class_names or M.CLASS_NAMES, "thresholds": thresholds or TEST_THRESHOLDS}))
    (directory / M.RESTORATION_CONFIG_FILE).write_text(json.dumps(default_config()))
    (directory / M.METADATA_FILE).write_text(json.dumps({
        "model_version": M.MODEL_VERSION, "class_names": M.CLASS_NAMES, "tile_size": M.TILE_SIZE,
        "preprocessing": {"mean": M.PIXEL_MEAN, "std": M.PIXEL_STD},
        "weights_sha256": M.file_sha256(directory / M.WEIGHTS_FILE)}))
    return directory


def make_scene(h=160, w=192, seed=0) -> np.ndarray:
    """Synthetic 'clean photo': smooth gradient, coloured shapes, mild texture. RGB uint8."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w]
    img = np.stack([40 + 180 * xx / w, 60 + 150 * yy / h, 200 - 120 * xx / w], axis=-1).astype(np.uint8)
    for _ in range(8):
        c = tuple(int(v) for v in rng.integers(20, 235, 3))
        cv2.circle(img, (int(rng.integers(0, w)), int(rng.integers(0, h))), int(rng.integers(8, 30)), c, -1)
        cv2.rectangle(img, (int(rng.integers(0, w)), int(rng.integers(0, h))),
                      (int(rng.integers(0, w)), int(rng.integers(0, h))), tuple(int(v) for v in rng.integers(20, 235, 3)), 2)
    img = np.clip(img.astype(np.float32) + rng.normal(0, 1.5, img.shape), 0, 255).astype(np.uint8)
    return img


def encode(img_rgb: np.ndarray, fmt: str, mode: str = "RGB") -> bytes:
    pil = Image.fromarray(img_rgb)
    if mode != "RGB":
        pil = pil.convert(mode)
    buf = io.BytesIO()
    pil.save(buf, format=fmt)
    return buf.getvalue()


@pytest.fixture(scope="session")
def artifact_dir(tmp_path_factory) -> Path:
    return write_artifacts(tmp_path_factory.mktemp("artifacts"))


@pytest.fixture(scope="session")
def predictor(artifact_dir):
    return M.DegradationPredictor(artifact_dir, device="cpu")


@pytest.fixture(scope="session")
def scene():
    return make_scene()


def _settings(tmp_path_factory, artifacts: Path, **overrides) -> Settings:
    base = Settings(artifacts_dir=artifacts, restored_dir=tmp_path_factory.mktemp("restored"),
                    max_upload_bytes=25 * 1024 * 1024, max_image_side=8000, min_image_side=32, max_pixels=16_000_000,
                    inline_base64_max_bytes=3 * 1024 * 1024, restored_ttl_seconds=3600, max_concurrent_jobs=2, device="cpu")
    return replace(base, **overrides)


@pytest.fixture(scope="module")
def client(tmp_path_factory, artifact_dir):
    with TestClient(create_app(_settings(tmp_path_factory, artifact_dir)), raise_server_exceptions=False) as c:
        yield c


@pytest.fixture(scope="module")
def small_limit_client(tmp_path_factory, artifact_dir):
    s = _settings(tmp_path_factory, artifact_dir, max_upload_bytes=60_000, max_image_side=300, max_pixels=40_000)
    with TestClient(create_app(s)) as c:
        yield c


@pytest.fixture(scope="module")
def no_model_client(tmp_path_factory):
    empty = tmp_path_factory.mktemp("empty_artifacts")
    with TestClient(create_app(_settings(tmp_path_factory, empty))) as c:
        yield c
