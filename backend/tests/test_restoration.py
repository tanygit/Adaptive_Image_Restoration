import json

import cv2
import numpy as np
import pytest

import degradations as D
import restoration as R
from conftest import make_scene
from evaluation import psnr, ssim
from image_quality import compute_quality_stats

ALL = {n: True for n in R.OPERATION_NAMES}
rng = lambda s=0: np.random.default_rng(s)


@pytest.fixture(scope="module")
def clean():
    return make_scene(192, 224, seed=3)


@pytest.fixture(scope="module")
def restorer():
    return R.Restorer()


def only(name):
    return {name: True}


def test_low_light_raises_brightness_without_clipping_everything(clean, restorer):
    dark = D.apply_low_light(clean, gamma=3.0, gain=0.7)
    out = restorer.restore(dark, only("low_light"))
    assert [o["operation"] for o in out.operations] == ["gamma_correction_lightness"]
    before, after = compute_quality_stats(dark), compute_quality_stats(out.image)
    assert after["mean_luminance"] > before["mean_luminance"] + 15
    assert after["mean_luminance"] < 200  # controlled: not blown out
    assert psnr(clean, out.image) > psnr(clean, dark)


def test_low_light_is_skipped_on_bright_image(restorer):
    bright = np.full((96, 96, 3), 200, np.uint8)
    out = restorer.restore(bright, only("low_light"))
    assert out.operations == [] and out.skipped and out.skipped[0]["degradation"] == "low_light"
    assert np.array_equal(out.image, bright)


def test_low_contrast_expands_tonal_range(clean, restorer):
    flat = D.apply_low_contrast(clean, alpha=0.3, shift=0.0)
    out = restorer.restore(flat, only("low_contrast"))
    assert out.operations[0]["operation"] == "stretch_plus_clahe_lightness"
    assert compute_quality_stats(out.image)["dynamic_range_p5_p95"] > compute_quality_stats(flat)["dynamic_range_p5_p95"] + 20
    assert psnr(clean, out.image) > psnr(clean, flat)


def test_gaussian_noise_reduction_improves_psnr(clean, restorer):
    noisy = D.apply_gaussian_noise(clean, 20, rng(1))
    out = restorer.restore(noisy, only("gaussian_noise"))
    assert out.operations[0]["operation"] == "non_local_means_denoise"
    assert 12 < out.operations[0]["parameters"]["estimated_sigma"] < 28
    assert psnr(clean, out.image) > psnr(clean, noisy) + 1.0


def test_salt_pepper_removal_is_selective(clean, restorer):
    noisy = D.apply_salt_pepper(clean, 0.05, rng(2))
    out = restorer.restore(noisy, only("salt_pepper_noise"))
    assert out.operations[0]["operation"] == "selective_median_filter"
    assert psnr(clean, out.image) > psnr(clean, noisy) + 5.0
    changed = np.mean(np.any(out.image != noisy, axis=2))
    assert changed < 0.2  # most pixels untouched (a full median blur would change far more)


def test_blur_sharpening_is_conservative_and_warns(clean, restorer):
    blurred = D.apply_blur(clean, "gaussian", 2.0, 9, 0)
    out = restorer.restore(blurred, only("blur"))
    assert out.operations[0]["operation"] == "conservative_unsharp_mask"
    assert any("NOT deblurring" in w for w in out.warnings)
    assert compute_quality_stats(out.image)["laplacian_variance"] >= compute_quality_stats(blurred)["laplacian_variance"]
    assert np.abs(out.image.astype(int) - blurred.astype(int)).max() < 120  # no wild overshoot


def test_output_shape_dtype_preserved(clean, restorer):
    out = restorer.restore(clean, ALL, use_guards=False).image
    assert out.shape == clean.shape and out.dtype == np.uint8


def test_nothing_detected_returns_identical_image(clean, restorer):
    out = restorer.restore(clean, {})
    assert out.operations == [] and np.array_equal(out.image, clean)


def test_combined_degradations_follow_configured_order(clean, restorer):
    degraded, labels, _ = D.degrade(clean, rng(5), labels=list(R.OPERATION_NAMES), severities=["moderate"])
    out = restorer.restore(degraded, ALL, use_guards=False)
    assert [o["degradation"] for o in out.operations] == ["salt_pepper_noise", "low_light", "gaussian_noise", "low_contrast", "blur"]
    assert all(o["reason"] for o in out.operations)


def test_combined_adaptive_beats_degraded(clean, restorer):
    degraded, _, _ = D.degrade(clean, rng(6), labels=["low_light", "gaussian_noise", "salt_pepper_noise"], severities=["moderate"])
    out = restorer.restore(degraded, {"low_light": True, "gaussian_noise": True, "salt_pepper_noise": True})
    assert psnr(clean, out.image) > psnr(clean, degraded)
    assert ssim(clean, out.image) > ssim(clean, degraded)


@pytest.mark.parametrize("strength", R.STRENGTHS)
def test_each_strength_mode_runs(clean, restorer, strength):
    degraded, _, _ = D.degrade(clean, rng(7), labels=["low_contrast", "gaussian_noise"], severities=["moderate"])
    out = restorer.restore(degraded, {"low_contrast": True, "gaussian_noise": True}, strength)
    assert len(out.operations) == 2


def test_strength_ordering_for_low_light(clean, restorer):
    dark = D.apply_low_light(clean, gamma=3.5, gain=0.6)
    means = [compute_quality_stats(restorer.restore(dark, only("low_light"), s).image)["mean_luminance"] for s in R.STRENGTHS]
    assert means[0] < means[1] < means[2]


def test_strength_ordering_for_denoising(clean, restorer):
    noisy = D.apply_gaussian_noise(clean, 25, rng(8))
    hs = [restorer.restore(noisy, only("gaussian_noise"), s).operations[0]["parameters"]["h"] for s in R.STRENGTHS]
    assert hs[0] < hs[1] < hs[2]


def test_invalid_strength_rejected(clean, restorer):
    with pytest.raises(ValueError):
        restorer.restore(clean, ALL, "extreme")


def test_fixed_baseline_applies_every_operation(clean, restorer):
    out = restorer.restore_fixed_baseline(clean)
    assert {o["degradation"] for o in out.operations} >= {"salt_pepper_noise", "gaussian_noise", "low_contrast", "blur"}


def test_config_validation_and_override(tmp_path):
    cfg = R.default_config()
    cfg["operation_order"] = ["blur", "low_light", "gaussian_noise", "low_contrast", "salt_pepper_noise"]
    path = tmp_path / "cfg.json"
    path.write_text(json.dumps(cfg))
    assert R.load_config(path)["operation_order"][0] == "blur"
    cfg["operation_order"] = ["blur"]
    path.write_text(json.dumps(cfg))
    with pytest.raises(ValueError):
        R.load_config(path)
    assert R.load_config(tmp_path / "missing.json") == R.default_config()


def test_ssim_and_psnr_sanity(clean):
    assert psnr(clean, clean) == 50.0 and ssim(clean, clean) == pytest.approx(1.0)
    noisy = D.apply_gaussian_noise(clean, 20, rng(9))
    assert 15 < psnr(clean, noisy) < 30 and ssim(clean, noisy) < 0.95


def test_degradation_labels_and_clean_examples():
    img = make_scene()
    out, label, params = D.degrade(img, rng(0), labels=["blur", "gaussian_noise"])
    assert label.tolist() == [0, 0, 1, 0, 1] and set(params) == {"blur", "gaussian_noise"}
    _, label, _ = D.degrade(img, rng(0), labels=[])
    assert label.sum() == 0
    with pytest.raises(ValueError):
        D.degrade(img, rng(0), labels=["rain"])
