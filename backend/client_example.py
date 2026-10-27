"""
client_example.py - upload one image to the running API, print the diagnostics and save the restored PNG.

    python client_example.py test_images\\photo.jpg --strength balanced --out restored.png
Requires: pip install requests   (included in requirements-dev.txt)
"""
import argparse
import os
import sys
from pathlib import Path

import requests


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("image", type=Path)
    ap.add_argument("--url", default="http://127.0.0.1:8000")
    ap.add_argument("--strength", choices=["gentle", "balanced", "strong"], default="balanced")
    ap.add_argument("--out", type=Path, default=Path("restored.png"))
    ap.add_argument("--open", action="store_true", help="open the result in the default viewer (Windows)")
    args = ap.parse_args()

    with open(args.image, "rb") as fh:
        resp = requests.post(f"{args.url}/restore", params={"strength": args.strength, "response_image": "url"},
                             files={"file": (args.image.name, fh)}, timeout=300)
    if resp.status_code != 200:
        print(f"Request failed ({resp.status_code}): {resp.json().get('error', resp.text)}", file=sys.stderr)
        return 1
    body = resp.json()
    print("Detected:", ", ".join(body["detected_degradations"]) or "nothing above threshold")
    for name, d in body["detections"].items():
        print(f"  {name:20s} p={d['probability']:.3f} threshold={d['threshold']:.2f} detected={d['detected']}")
    for op in body["selected_operations"]:
        print(f"Applied {op['operation']}: {op['reason']}")
    for skipped in body["skipped_operations"]:
        print(f"Skipped {skipped['degradation']}: {skipped['reason']}")
    for key in ("mean_luminance", "contrast_std", "laplacian_variance", "noise_sigma_estimate"):
        print(f"  {key:22s} before={body['quality_before'][key]:>9} after={body['quality_after'][key]:>9}")
    print(f"Processing time: {body['processing_time_seconds']} s")
    for w in body["warnings"]:
        print("Warning:", w)
    img = requests.get(f"{args.url}{body['restored_image_url']}", timeout=60)
    img.raise_for_status()
    args.out.write_bytes(img.content)
    print("Saved", args.out.resolve())
    if args.open and hasattr(os, "startfile"):
        os.startfile(str(args.out))  # type: ignore[attr-defined]
    return 0


if __name__ == "__main__":
    sys.exit(main())
