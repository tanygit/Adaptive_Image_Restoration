import csv

import cv2
import numpy as np

import degradations as D
import evaluation as E
from conftest import make_scene
from model import CLASS_NAMES


def _make_pairs(root, n=4):
    (root / "clean").mkdir(); (root / "degraded").mkdir()
    rows = []
    for i in range(n):
        clean = make_scene(144, 160, seed=i)
        deg, label, _ = D.degrade(clean, np.random.default_rng(i), labels=[CLASS_NAMES[i % 5]], severities=["moderate"])
        for folder, img in (("clean", clean), ("degraded", deg)):
            cv2.imwrite(str(root / folder / f"p{i}.png"), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
        rows.append([f"p{i}.png"] + [int(x) for x in label])
    with open(root / "labels.csv", "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["filename"] + CLASS_NAMES); w.writerows(rows)
    return E.read_labels_csv(root / "labels.csv")


def test_restoration_evaluation_with_ground_truth_detector(tmp_path, artifact_dir):
    labels = _make_pairs(tmp_path)
    rep = E.evaluate_restoration(tmp_path / "clean", tmp_path / "degraded", labels, "labels", artifact_dir, "balanced")
    o = rep["overall"]
    assert o["n_images"] == 4 and o["adaptive_psnr_improved"] + o["adaptive_psnr_worsened"] + o["adaptive_psnr_unchanged"] == 4
    assert o["mean_psnr_adaptive"] > o["mean_psnr_degraded"]
    assert set(rep["per_category_images_containing_label"]) <= set(CLASS_NAMES) | {"no_degradation"}
    assert len(rep["per_image"]) == 4


def test_restoration_evaluation_with_model_detector(tmp_path, artifact_dir):
    _make_pairs(tmp_path)
    rep = E.evaluate_restoration(tmp_path / "clean", tmp_path / "degraded", None, "model", artifact_dir, "gentle")
    assert rep["overall"]["n_images"] == 4 and rep["per_category_images_containing_label"] == {}


def test_classifier_evaluation_report(tmp_path, artifact_dir):
    labels = _make_pairs(tmp_path)
    rep = E.evaluate_classifier(tmp_path / "degraded", labels, artifact_dir)
    assert rep["n_images"] == 4 and set(rep["per_class"]) == set(CLASS_NAMES) and 0 <= rep["macro_f1"] <= 1


def test_multilabel_report_values():
    y_true = np.array([[1, 0, 0, 0, 0], [1, 1, 0, 0, 0], [0, 0, 0, 0, 0]])
    y_pred = np.array([[1, 0, 0, 0, 0], [0, 1, 0, 0, 0], [1, 0, 0, 0, 0]])
    rep = E.multilabel_report(y_true, y_pred)
    low_light = rep["per_class"]["low_light"]
    assert (low_light["tp"], low_light["fp"], low_light["fn"]) == (1, 1, 1) and abs(low_light["f1"] - 0.5) < 1e-9
    assert abs(rep["micro_f1"] - 2 / 3) < 1e-9 and abs(rep["exact_match_ratio"] - 1 / 3) < 1e-9


def test_cli_refuses_non_test_manifest(tmp_path, artifact_dir):
    _make_pairs(tmp_path)
    (tmp_path / "m.json").write_text('{"split": "val"}')
    code = E.main(["restoration", "--clean-dir", str(tmp_path / "clean"), "--degraded-dir", str(tmp_path / "degraded"),
                   "--manifest", str(tmp_path / "m.json"), "--artifacts-dir", str(artifact_dir)])
    assert code == 2
