"""
evaluation.py - metrics and command-line evaluation tools.

Two SEPARATE evaluations (never mix them):
  1) `classifier`   : how well are degradations DETECTED?  Needs images + ground-truth labels (CSV).
                      Use REAL degraded photographs that you labelled yourself for an honest real-world number.
  2) `restoration`  : does the restoration improve images?  Needs paired clean + degraded images, because
                      PSNR/SSIM are reference-based and are meaningless without a clean reference.

Examples (from the backend folder, virtual environment active):
  python evaluation.py restoration --clean-dir pairs\\clean --degraded-dir pairs\\degraded ^
         --labels-csv pairs\\labels.csv --manifest pairs\\manifest.json --detector labels --out eval_report
  python evaluation.py restoration --clean-dir pairs\\clean --degraded-dir pairs\\degraded --detector model
  python evaluation.py classifier --images-dir my_real_photos --labels-csv my_real_photos\\labels.csv

Interpreting restoration numbers: PSNR is in dB (higher = closer to the clean image, capped at 50 dB; +1 dB is
noticeable, +0.2 dB is marginal); SSIM is 0..1 (higher = more structurally similar). Both can disagree with human taste
(e.g. CLAHE can look better yet lower PSNR). Compare the three rows - degraded, fixed baseline, adaptive - and
read the improved/worsened counts, not just the mean.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import cv2
import numpy as np

from model import CLASS_NAMES, DegradationPredictor
from restoration import Restorer, load_config

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


# --------------------------------------------------------------------------------------
# Reference-based metrics
# --------------------------------------------------------------------------------------
PSNR_CAP_DB = 50.0  # identical images give infinite PSNR; capping keeps averages meaningful


def psnr(reference: np.ndarray, test: np.ndarray) -> float:
    """PSNR in dB for uint8 images of equal shape, capped at PSNR_CAP_DB (identical images return the cap)."""
    if reference.shape != test.shape:
        raise ValueError(f"Shape mismatch: {reference.shape} vs {test.shape}")
    mse = float(np.mean((reference.astype(np.float64) - test.astype(np.float64)) ** 2))
    return PSNR_CAP_DB if mse == 0 else float(min(PSNR_CAP_DB, 10.0 * np.log10(255.0 ** 2 / mse)))


def ssim(reference: np.ndarray, test: np.ndarray) -> float:
    """Mean SSIM (Wang et al. 2004; 11x11 Gaussian window, sigma 1.5) averaged over RGB channels."""
    if reference.shape != test.shape:
        raise ValueError(f"Shape mismatch: {reference.shape} vs {test.shape}")
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    a, b = reference.astype(np.float64), test.astype(np.float64)
    scores = []
    for ch in range(a.shape[2]):
        x, y = a[..., ch], b[..., ch]
        blur = lambda z: cv2.GaussianBlur(z, (11, 11), 1.5, borderType=cv2.BORDER_REFLECT_101)
        mx, my = blur(x), blur(y)
        sxx, syy, sxy = blur(x * x) - mx * mx, blur(y * y) - my * my, blur(x * y) - mx * my
        s = ((2 * mx * my + c1) * (2 * sxy + c2)) / ((mx ** 2 + my ** 2 + c1) * (sxx + syy + c2))
        scores.append(float(s.mean()))
    return float(np.mean(scores))


def binary_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Precision / recall / F1 / support and confusion counts for one binary label."""
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1, "support": tp + fn, "tp": tp, "fp": fp, "fn": fn, "tn": tn}


def multilabel_report(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """Per-class metrics plus micro/macro F1 (shared with the notebook's logic, re-implemented without sklearn)."""
    per_class = {name: binary_metrics(y_true[:, i], y_pred[:, i]) for i, name in enumerate(CLASS_NAMES)}
    tp = sum(m["tp"] for m in per_class.values())
    fp = sum(m["fp"] for m in per_class.values())
    fn = sum(m["fn"] for m in per_class.values())
    micro_p, micro_r = tp / (tp + fp) if tp + fp else 0.0, tp / (tp + fn) if tp + fn else 0.0
    micro_f1 = 2 * micro_p * micro_r / (micro_p + micro_r) if micro_p + micro_r else 0.0
    return {"per_class": per_class, "micro_f1": micro_f1,
            "macro_f1": float(np.mean([m["f1"] for m in per_class.values()])),
            "exact_match_ratio": float(np.mean(np.all(y_true == y_pred, axis=1)))}


# --------------------------------------------------------------------------------------
# File helpers
# --------------------------------------------------------------------------------------
def read_rgb(path: Path) -> np.ndarray:
    data = np.fromfile(str(path), dtype=np.uint8)  # works with non-ASCII Windows paths
    bgr = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError(f"Could not decode image: {path}")
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def read_labels_csv(path: Path) -> Dict[str, np.ndarray]:
    """CSV columns: filename + one 0/1 column per class name. Keyed by file stem."""
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    missing = [c for c in ["filename"] + CLASS_NAMES if rows and c not in rows[0]]
    if not rows or missing:
        raise ValueError(f"{path} must have columns: filename, {', '.join(CLASS_NAMES)} (missing: {missing})")
    return {Path(r["filename"]).stem: np.array([int(r[c]) for c in CLASS_NAMES]) for r in rows}


def list_images(directory: Path) -> Dict[str, Path]:
    return {p.stem: p for p in sorted(directory.iterdir()) if p.suffix.lower() in IMAGE_SUFFIXES}


# --------------------------------------------------------------------------------------
# Restoration evaluation
# --------------------------------------------------------------------------------------
def evaluate_restoration(clean_dir: Path, degraded_dir: Path, labels: Optional[Dict[str, np.ndarray]],
                         detector: str, artifacts_dir: Path, strength: str) -> dict:
    clean, degraded = list_images(clean_dir), list_images(degraded_dir)
    stems = sorted(set(clean) & set(degraded))
    if not stems:
        raise ValueError("No image pairs found: clean and degraded files must share the same file name stem.")
    restorer = Restorer(load_config(artifacts_dir / "restoration_config.json"))
    predictor = DegradationPredictor(artifacts_dir) if detector == "model" else None
    if detector == "labels" and labels is None:
        raise ValueError("--detector labels needs --labels-csv")

    rows: List[dict] = []
    for stem in stems:
        ref, deg = read_rgb(clean[stem]), read_rgb(degraded[stem])
        if ref.shape != deg.shape:
            raise ValueError(f"Pair '{stem}' has different sizes: {ref.shape} vs {deg.shape}")
        if predictor is not None:
            detected = {n: v["detected"] for n, v in predictor.predict(deg).items()}
        else:
            detected = {n: bool(labels[stem][i]) for i, n in enumerate(CLASS_NAMES)}  # type: ignore[index]
        t0 = time.perf_counter(); base = restorer.restore_fixed_baseline(deg, strength).image
        t1 = time.perf_counter(); adapt = restorer.restore(deg, detected, strength).image
        t2 = time.perf_counter()
        row = {"image": stem, "baseline_seconds": t1 - t0, "adaptive_seconds": t2 - t1,
               "true_labels": [n for i, n in enumerate(CLASS_NAMES) if labels is not None and stem in labels and labels[stem][i]],
               "applied": [n for n, v in detected.items() if v]}
        for tag, img in (("degraded", deg), ("baseline", base), ("adaptive", adapt)):
            row[f"psnr_{tag}"], row[f"ssim_{tag}"] = psnr(ref, img), ssim(ref, img)
        rows.append(row)

    def summarize(subset: List[dict]) -> dict:
        out = {"n_images": len(subset)}
        for tag in ("degraded", "baseline", "adaptive"):
            out[f"mean_psnr_{tag}"] = statistics.fmean(r[f"psnr_{tag}"] for r in subset)
            out[f"mean_ssim_{tag}"] = statistics.fmean(r[f"ssim_{tag}"] for r in subset)
        for tag in ("baseline", "adaptive"):
            d = [r[f"psnr_{tag}"] - r["psnr_degraded"] for r in subset]
            out[f"{tag}_psnr_improved"] = sum(x > 0.05 for x in d)
            out[f"{tag}_psnr_worsened"] = sum(x < -0.05 for x in d)
            out[f"{tag}_psnr_unchanged"] = len(d) - out[f"{tag}_psnr_improved"] - out[f"{tag}_psnr_worsened"]
            out[f"{tag}_mean_psnr_gain_db"] = statistics.fmean(d)
        out["mean_seconds_baseline"] = statistics.fmean(r["baseline_seconds"] for r in subset)
        out["mean_seconds_adaptive"] = statistics.fmean(r["adaptive_seconds"] for r in subset)
        return out

    per_category = {}
    if labels is not None:
        for name in CLASS_NAMES:
            subset = [r for r in rows if name in r["true_labels"]]
            if subset:
                per_category[name] = summarize(subset)
        clean_subset = [r for r in rows if not r["true_labels"] and r["image"] in labels]
        if clean_subset:
            per_category["no_degradation"] = summarize(clean_subset)
    return {"detector": detector, "strength": strength, "overall": summarize(rows),
            "per_category_images_containing_label": per_category, "per_image": rows,
            "note": "Reference-based metrics against clean originals. PSNR 'improved/worsened' uses a +-0.05 dB dead zone."}


# --------------------------------------------------------------------------------------
# Classifier evaluation on labelled images (ideally real degraded photographs)
# --------------------------------------------------------------------------------------
def evaluate_classifier(images_dir: Path, labels: Dict[str, np.ndarray], artifacts_dir: Path) -> dict:
    predictor = DegradationPredictor(artifacts_dir)
    images = list_images(images_dir)
    stems = [s for s in sorted(labels) if s in images]
    if not stems:
        raise ValueError("None of the labelled file names were found in --images-dir.")
    y_true = np.stack([labels[s] for s in stems])
    y_pred = np.zeros_like(y_true)
    for k, stem in enumerate(stems):
        pred = predictor.predict(read_rgb(images[stem]))
        y_pred[k] = [int(pred[n]["detected"]) for n in CLASS_NAMES]
    report = multilabel_report(y_true, y_pred)
    report["n_images"] = len(stems)
    report["note"] = ("Computed on the images you supplied. Only treat this as real-world performance if they are real "
                      "photographs with trustworthy labels that were never used for training or threshold tuning.")
    return report


def _print_summary(title: str, s: dict) -> None:
    print(f"\n{title}  (n={s['n_images']})")
    print(f"  {'':10s}{'PSNR dB':>10s}{'SSIM':>9s}")
    for tag in ("degraded", "baseline", "adaptive"):
        print(f"  {tag:10s}{s['mean_psnr_' + tag]:10.2f}{s['mean_ssim_' + tag]:9.4f}")
    for tag in ("baseline", "adaptive"):
        print(f"  {tag}: improved {s[tag + '_psnr_improved']}, worsened {s[tag + '_psnr_worsened']}, unchanged "
              f"{s[tag + '_psnr_unchanged']}, mean gain {s[tag + '_mean_psnr_gain_db']:+.2f} dB")
    print(f"  mean runtime: baseline {s['mean_seconds_baseline']:.2f}s, adaptive {s['mean_seconds_adaptive']:.2f}s")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    r = sub.add_parser("restoration", help="paired clean/degraded evaluation (PSNR, SSIM)")
    r.add_argument("--clean-dir", type=Path, required=True)
    r.add_argument("--degraded-dir", type=Path, required=True)
    r.add_argument("--labels-csv", type=Path, help="ground-truth labels (enables per-category results / oracle detector)")
    r.add_argument("--manifest", type=Path, help="manifest.json written by the notebook for held-out test pairs")
    r.add_argument("--detector", choices=["model", "labels"], default="model",
                   help="'model' = trained classifier decides; 'labels' = ground truth decides (isolates restoration quality)")
    r.add_argument("--strength", choices=["gentle", "balanced", "strong"], default="balanced")
    r.add_argument("--artifacts-dir", type=Path, default=Path(__file__).resolve().parent / "artifacts")
    r.add_argument("--out", type=Path, help="output prefix; writes <prefix>.json and <prefix>_per_image.csv")
    c = sub.add_parser("classifier", help="multi-label detection metrics on labelled images")
    c.add_argument("--images-dir", type=Path, required=True)
    c.add_argument("--labels-csv", type=Path, required=True)
    c.add_argument("--artifacts-dir", type=Path, default=Path(__file__).resolve().parent / "artifacts")
    c.add_argument("--out", type=Path, help="write the report as JSON")
    args = parser.parse_args(argv)

    try:
        if args.command == "classifier":
            report = evaluate_classifier(args.images_dir, read_labels_csv(args.labels_csv), args.artifacts_dir)
            print(f"\nClassifier evaluation on {report['n_images']} images")
            for name, m in report["per_class"].items():
                print(f"  {name:20s} P={m['precision']:.3f} R={m['recall']:.3f} F1={m['f1']:.3f} support={m['support']}")
            print(f"  micro-F1={report['micro_f1']:.3f} macro-F1={report['macro_f1']:.3f} exact-match={report['exact_match_ratio']:.3f}")
            if args.out:
                args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
            return 0

        if args.manifest:
            manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
            if manifest.get("split") != "test":
                print(f"REFUSING: manifest says split={manifest.get('split')!r}; only held-out 'test' pairs are valid.", file=sys.stderr)
                return 2
        else:
            print("WARNING: no --manifest given; cannot verify these pairs were excluded from training/validation.", file=sys.stderr)
        labels = read_labels_csv(args.labels_csv) if args.labels_csv else None
        report = evaluate_restoration(args.clean_dir, args.degraded_dir, labels, args.detector, args.artifacts_dir, args.strength)
        _print_summary("OVERALL", report["overall"])
        for name, s in report["per_category_images_containing_label"].items():
            _print_summary(f"IMAGES CONTAINING '{name}'", s)
        if args.out:
            args.out.with_suffix(".json").write_text(json.dumps(report, indent=2), encoding="utf-8")
            with open(f"{args.out}_per_image.csv", "w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                keys = [k for k in report["per_image"][0] if k not in ("true_labels", "applied")]
                w.writerow(keys + ["true_labels", "applied"])
                for row in report["per_image"]:
                    w.writerow([row[k] for k in keys] + ["|".join(row["true_labels"]), "|".join(row["applied"])])
        return 0
    except (ValueError, OSError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
