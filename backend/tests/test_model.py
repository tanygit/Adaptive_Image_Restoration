import json

import numpy as np
import pytest
import torch

import model as M
from conftest import TEST_THRESHOLDS, make_scene, write_artifacts


def test_model_loads_and_is_in_eval_mode(predictor):
    assert predictor.model.training is False
    assert predictor.device.type == "cpu"
    assert M.count_parameters(predictor.model) < 1_000_000  # "lightweight"


def test_multilabel_output_format(predictor, scene):
    out = predictor.predict(scene)
    assert list(out.keys()) == M.CLASS_NAMES
    for name, item in out.items():
        assert set(item) == {"probability", "threshold", "detected"}
        assert 0.0 <= item["probability"] <= 1.0
        assert item["threshold"] == TEST_THRESHOLDS[name]
        assert isinstance(item["detected"], bool)


def test_thresholds_are_applied_per_class(predictor, scene):
    for name, item in predictor.predict(scene).items():
        assert item["detected"] == (item["probability"] >= TEST_THRESHOLDS[name])


def test_apply_thresholds_boundaries():
    th = {n: 0.5 for n in M.CLASS_NAMES}
    assert M.apply_thresholds([0.49, 0.5, 0.51, 0.0, 1.0], th) == [False, True, True, False, True]
    th["blur"] = 0.9
    assert M.apply_thresholds([0.5] * 5, th) == [True, True, True, True, False]


def test_prediction_is_deterministic(predictor, scene):
    assert predictor.predict(scene) == predictor.predict(scene)


def test_rgb_uint8_required(predictor):
    with pytest.raises(ValueError):
        M.extract_tiles(np.zeros((64, 64), np.uint8))  # grayscale is not accepted here (decoder converts to RGB)
    with pytest.raises(ValueError):
        M.extract_tiles(np.zeros((64, 64, 3), np.float32))


@pytest.mark.parametrize("shape,expected_tiles", [((40, 50, 3), 1), ((128, 128, 3), 1), ((300, 300, 3), 9), ((130, 400, 3), 6)])
def test_tiling_shapes_and_padding(shape, expected_tiles):
    tiles = M.extract_tiles(np.random.default_rng(0).integers(0, 255, shape, dtype=np.uint8))
    assert tiles.shape == (expected_tiles, M.TILE_SIZE, M.TILE_SIZE, 3)


def test_tiles_are_native_resolution_not_resized():
    img = np.random.default_rng(1).integers(0, 255, (128, 256, 3), dtype=np.uint8)
    tiles = M.extract_tiles(img)
    assert np.array_equal(tiles[0], img[:, :128]) and np.array_equal(tiles[-1], img[:, 128:])


def test_preprocessing_range():
    x = M.tiles_to_tensor(np.array([np.zeros((128, 128, 3), np.uint8), np.full((128, 128, 3), 255, np.uint8)]))
    assert x.min().item() == -1.0 and x.max().item() == 1.0 and x.shape == (2, 3, 128, 128)


def test_small_and_large_images_work(predictor):
    for shape in [(32, 32), (700, 900)]:
        assert len(predictor.predict(make_scene(*shape))) == 5


def test_missing_weights_gives_clear_error(tmp_path):
    with pytest.raises(M.ArtifactError, match="Model weights not found"):
        M.DegradationPredictor(tmp_path)


def test_class_order_mismatch_is_rejected(tmp_path):
    write_artifacts(tmp_path, class_names=list(reversed(M.CLASS_NAMES)))
    with pytest.raises(M.ArtifactError, match="class order"):
        M.DegradationPredictor(tmp_path)


def test_corrupt_weights_hash_is_rejected(tmp_path):
    write_artifacts(tmp_path)
    (tmp_path / M.WEIGHTS_FILE).write_bytes(b"not a checkpoint")
    with pytest.raises(M.ArtifactError):
        M.DegradationPredictor(tmp_path)


def test_incompatible_metadata_is_rejected(tmp_path):
    write_artifacts(tmp_path)
    meta = json.loads((tmp_path / M.METADATA_FILE).read_text())
    meta["tile_size"] = 64
    (tmp_path / M.METADATA_FILE).write_text(json.dumps(meta))
    with pytest.raises(M.ArtifactError, match="tile_size"):
        M.DegradationPredictor(tmp_path)


@pytest.mark.parametrize("bad", [0.0, 1.0, -0.2, "0.5"])
def test_invalid_thresholds_are_rejected(bad):
    th = dict(TEST_THRESHOLDS, blur=bad)
    with pytest.raises(M.ArtifactError):
        M.validate_thresholds({"class_names": M.CLASS_NAMES, "thresholds": th})
