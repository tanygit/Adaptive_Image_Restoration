import base64
import io
import json

import cv2
import numpy as np
from PIL import Image

import degradations as D
from conftest import encode, make_scene

CLASSES = ["low_light", "low_contrast", "gaussian_noise", "salt_pepper_noise", "blur"]


def post(client, data, name="photo.png", ctype="image/png", **params):
    return client.post("/restore", files={"file": (name, data, ctype)}, params=params)


def decode_b64(b64):
    return cv2.imdecode(np.frombuffer(base64.b64decode(b64), np.uint8), cv2.IMREAD_COLOR)


# ------------------------------------------------------------------ info / health
def test_root(client):
    body = client.get("/").json()
    assert body["degradation_classes"] == CLASSES and "POST /restore" in body["endpoints"]["restore"]


def test_health(client):
    r = client.get("/health")
    body = r.json()
    assert r.status_code == 200 and body["status"] == "ok" and body["model_loaded"] is True
    assert body["device"] == "cpu" and set(body["thresholds"]) == set(CLASSES)


def test_docs_available(client):
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200


def test_missing_model_reports_clearly(no_model_client):
    health = no_model_client.get("/health")
    assert health.status_code == 503 and health.json()["model_loaded"] is False and "not found" in health.json()["error"]
    r = post(no_model_client, encode(make_scene(), "PNG"))
    assert r.status_code == 503 and r.json()["error"]["code"] == "model_unavailable"


# ------------------------------------------------------------------ successful restore
def test_restore_response_structure_and_returned_image(client):
    clean = make_scene(160, 200)
    degraded, _, _ = D.degrade(clean, np.random.default_rng(0), labels=["gaussian_noise"], severities=["severe"])
    r = post(client, encode(degraded, "PNG"), name="../../evil\\name.png", strength="strong")
    assert r.status_code == 200, r.text
    b = r.json()
    for key in ["request_id", "filename", "strength", "restored_image_url", "restored_image_base64", "detected_degradations",
                "detections", "selected_operations", "skipped_operations", "quality_before", "quality_after", "quality_change",
                "quality_notes", "processing_time_seconds", "timing_seconds", "warnings", "limitations"]:
        assert key in b, key
    assert b["filename"] == "name.png" and b["strength"] == "strong"
    assert list(b["detections"]) == CLASSES
    assert set(b["detections"]["blur"]) == {"probability", "threshold", "detected"}
    assert b["processing_time_seconds"] > 0
    assert {"mean_luminance", "contrast_std", "laplacian_variance", "width", "height"} <= set(b["quality_before"])
    for stats in (b["quality_before"], b["quality_after"], b["quality_change"]):  # no reference-based metrics for uploads
        assert not any("psnr" in k or "ssim" in k for k in stats)
    # returned base64 decodes to an image of the same size
    img = decode_b64(b["restored_image_base64"])
    assert img.shape[:2] == degraded.shape[:2]
    # the URL returns the same PNG
    dl = client.get(b["restored_image_url"])
    assert dl.status_code == 200 and dl.headers["content-type"] == "image/png"
    assert np.array_equal(cv2.imdecode(np.frombuffer(dl.content, np.uint8), cv2.IMREAD_COLOR), img)
    # applied operations correspond to detected classes and carry reasons
    considered = {o["degradation"] for o in b["selected_operations"]} | {s["degradation"] for s in b["skipped_operations"]}
    assert considered == set(b["detected_degradations"])
    assert all(o["reason"] for o in b["selected_operations"])


def test_all_supported_formats_and_modes(client):
    img = make_scene(96, 128)
    for fmt, mode in [("JPEG", "RGB"), ("PNG", "RGB"), ("WEBP", "RGB"), ("PNG", "L"), ("PNG", "RGBA"), ("PNG", "P")]:
        r = post(client, encode(img, fmt, mode), name=f"x.{fmt.lower()}", response_image="base64")
        assert r.status_code == 200, (fmt, mode, r.text)
        assert decode_b64(r.json()["restored_image_base64"]).shape == (96, 128, 3)


def test_response_image_modes(client):
    data = encode(make_scene(), "PNG")
    assert post(client, data, response_image="url").json()["restored_image_base64"] is None
    assert post(client, data, response_image="base64").json()["restored_image_base64"]


def test_default_strength_comes_from_config(client):
    assert post(client, encode(make_scene(), "PNG")).json()["strength"] == "balanced"


def test_invalid_strength_is_rejected(client):
    assert post(client, encode(make_scene(), "PNG"), strength="insane").status_code == 422


# ------------------------------------------------------------------ rejected uploads
def test_empty_upload(client):
    r = post(client, b"")
    assert r.status_code == 400 and r.json()["error"]["code"] == "empty_file"


def test_corrupt_upload(client):
    r = post(client, b"this is definitely not an image" * 20, name="a.jpg", ctype="image/jpeg")
    assert r.status_code == 415 and "Traceback" not in r.text


def test_truncated_image(client):
    data = encode(make_scene(200, 300), "JPEG")
    r = post(client, data[: len(data) // 2], name="t.jpg", ctype="image/jpeg")
    assert r.status_code == 422 and r.json()["error"]["code"] == "corrupt_image"


def test_unsupported_formats(client):
    for fmt in ("GIF", "BMP", "TIFF"):
        buf = io.BytesIO()
        Image.fromarray(make_scene(64, 64)).save(buf, format=fmt)
        r = post(client, buf.getvalue(), name="x.png", ctype="image/png")  # lying name/content-type must not matter
        assert r.status_code == 415 and r.json()["error"]["code"] == "unsupported_format", fmt


def test_png_extension_does_not_override_real_format(client):
    r = post(client, encode(make_scene(64, 64), "JPEG"), name="really_a_jpeg.png")
    assert r.status_code == 200


def test_oversized_file(small_limit_client):
    big = np.random.default_rng(0).integers(0, 255, (180, 220, 3), dtype=np.uint8)  # noise PNG >> 60 kB
    data = encode(big, "PNG")
    assert len(data) > 60_000
    r = post(small_limit_client, data)
    assert r.status_code == 413 and r.json()["error"]["code"] == "file_too_large"


def test_invalid_dimensions(client, small_limit_client):
    r = post(client, encode(np.zeros((16, 16, 3), np.uint8), "PNG"))
    assert r.status_code == 422 and r.json()["error"]["code"] == "image_too_small"
    r = post(small_limit_client, encode(np.zeros((40, 400, 3), np.uint8), "PNG"))
    assert r.status_code == 422 and r.json()["error"]["code"] == "image_too_large_dimensions"
    r = post(small_limit_client, encode(np.zeros((220, 220, 3), np.uint8), "PNG"))
    assert r.status_code == 422 and r.json()["error"]["code"] == "image_too_many_pixels"


def test_missing_file_field(client):
    assert client.post("/restore").status_code == 422


# ------------------------------------------------------------------ security / robustness
def test_download_rejects_path_traversal_and_unknown_ids(client):
    for bad in ["..%2F..%2Fconfig.py", "../main.py", "abc", "0" * 32, "G" * 32]:
        assert client.get(f"/restored/{bad}").status_code == 404


def test_internal_errors_do_not_leak_details(client, monkeypatch):
    def boom(_img):
        raise RuntimeError("secret internal detail /home/user/model.pth")
    monkeypatch.setattr(client.app.state.predictor, "predict", boom)
    r = post(client, encode(make_scene(), "PNG"))
    assert r.status_code == 500 and "secret" not in r.text and "Traceback" not in r.text
    assert r.json()["error"]["code"] == "internal_error"
