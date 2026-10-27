# Adaptive Image Restoration - backend

Upload ONE degraded image -> a small CNN detects which of five degradations are present (multi-label) -> matching
OpenCV restoration operations are applied -> you get the restored image plus transparent diagnostics.

Degradations: `low_light`, `low_contrast`, `gaussian_noise`, `salt_pepper_noise`, `blur` (any combination).

**Status you must know:** this source tree contains NO trained weights. Run the Colab notebook
(`colab_train_degradation_cnn.ipynb`) on your clean images, then copy its four artifact files into `artifacts/`.
Until then the API starts, `/health` returns 503 and `/restore` returns a clear `model_unavailable` error.

---------------------------------------------------------------------------------------------------

## A. Technical decisions

| Question | Decision and why |
|---|---|
| CNN from scratch or fine-tune? | **Small CNN from scratch** (~0.48 M parameters, 9 conv layers). The signal for noise, blur and impulses is in pixel-level detail; an ImageNet backbone expects resized 224x224 inputs, which erases exactly that detail, and adds ~10-25 MB of weights and a dependency on pretrained checkpoints. Fine-tuning is the fallback if real-photo accuracy turns out poor. |
| Is a custom CNN enough for 5 labels? | Yes for the synthetic recipes (verify with the test report). Whether it generalises to real photographs must be measured separately (see Part D). |
| Native resolution | Network input = native 128x128 **tiles** (up to 3x3 grid) of the image, logits averaged over tiles. Images with a longer side > 768 px are shrunk (INTER_AREA) before analysis (a warning is returned; fine noise/blur may be under-detected). |
| Synthetic data | Clean photos -> random 0-3 simultaneous degradations at mild/moderate/severe ranges, camera-like order (tone -> blur -> Gaussian noise -> impulse noise), 15 % clean examples, random rescaling. Ranges are recorded in `training_metadata.json`. |
| Separate models? | **One** model for detection. Restoration uses **no neural network**: transparent OpenCV operations, so every step can be explained. |
| OpenCV handles | low light (gamma on Lab lightness), low contrast (percentile stretch + CLAHE on lightness), Gaussian noise (non-local means, strength from a noise-sigma estimate), salt-and-pepper (selective median). |
| Unknown-kernel blur | **No deblurring is claimed.** Richardson-Lucy with a guessed kernel creates ringing; sharpening cannot recover lost detail. A conservative, halo-limited unsharp mask is applied and the response says so. A learned deblurring model would need testing, licensing review and extra dependencies, so it is not the default. |
| Resources | Colab: ~16 k patches/epoch, batch 128, mixed precision, <= 40 epochs with early stopping (epoch time on a T4 was NOT measured - only a CPU smoke run). Local: CPU only; classification ~35 ms for a small image on one CPU core; non-local means dominates (~3.8 s for a 4 MP noisy image on one core). |

### Restoration order (configurable in `restoration_config.json -> operation_order`)
1. impulse noise (smoothing would smear impulses) -> 2. low light (brightening amplifies noise, so denoise must see the final level)
-> 3. Gaussian noise -> 4. low contrast (CLAHE amplifies noise) -> 5. blur sharpening (last, on the final tone/noise state).
Operations run only for classes the classifier detected (probability >= calibrated threshold). Statistics-based guards may
**skip** an operation when a measurement clearly contradicts the classifier (e.g. "low light" on an image with mean lightness > 150);
every skip is reported. Statistics never add operations.
Strengths `gentle | balanced | strong` and all numeric parameters live in `restoration_config.json` (no code changes needed).

---------------------------------------------------------------------------------------------------

## Folder layout
```
backend/
  main.py            FastAPI app (endpoints, upload handling, response models)
  image_io.py        safe decoding / validation of uploads
  model.py           CNN, tiling, preprocessing, artifact loader   (shared with the Colab notebook)
  degradations.py    synthetic degradation generators              (shared with the notebook)
  image_quality.py   brightness / contrast / Laplacian variance / noise estimate
  restoration.py     OpenCV operations + adaptive pipeline + config validation
  evaluation.py      PSNR/SSIM + `classifier` and `restoration` evaluation CLIs
  config.py          settings from environment / .env (limits, paths)
  client_example.py  small upload client that saves the result
  artifacts/         <- put trained files here (see below)
  restored_images/   results (auto-deleted after RESTORED_TTL_SECONDS)
  test_images/       put your own test photos here
  tests/             pytest suite
```
Thresholds exist in ONE place: `artifacts/class_thresholds.json` (written by the notebook).

## B/E. Windows (CMD) - install, run, test
Requires 64-bit Python 3.10-3.12 (3.11 recommended). If Visual C++ errors appear on import of torch, install the
"Microsoft Visual C++ Redistributable (x64)".
```bat
cd adaptive_restoration\backend
py -3.11 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```
Place the trained artifacts (after running the notebook and downloading `deployment_artifacts.zip`):
```bat
mkdir "%TEMP%\da"
tar -xf "%USERPROFILE%\Downloads\deployment_artifacts.zip" -C "%TEMP%\da"
copy "%TEMP%\da\deployment_artifacts\degradation_cnn.pth" artifacts\
copy "%TEMP%\da\deployment_artifacts\class_thresholds.json" artifacts\
copy "%TEMP%\da\deployment_artifacts\restoration_config.json" artifacts\
copy "%TEMP%\da\deployment_artifacts\training_metadata.json" artifacts\
```
Start the server (Colab can be closed; nothing depends on it):
```bat
uvicorn main:app --host 127.0.0.1 --port 8000
```
In a second CMD window (activate the venv again for the Python client):
```bat
curl.exe http://127.0.0.1:8000/health
curl.exe -X POST -F "file=@test_images\photo.jpg" "http://127.0.0.1:8000/restore?strength=balanced&response_image=url" -o response.json
type response.json
python client_example.py test_images\photo.jpg --strength balanced --out restored.png --open
start restored.png
```
The same upload is available interactively at http://127.0.0.1:8000/docs.
Run the automated tests (they use temporary randomly-initialised weights only to test the plumbing, no artifacts needed):
```bat
python -m pytest -q
```

## API
* `GET /` info - `GET /health` (200 ok, or 503 with the reason when artifacts are missing/incompatible) - `GET /docs`
* `POST /restore?strength=gentle|balanced|strong&response_image=auto|base64|url` (multipart field `file`; JPEG/PNG/WebP)
* `GET /restored/{request_id}` downloads the PNG (id must be 32 hex chars; results expire after 1 h by default)

Response fields: `filename`, `strength`, `restored_image_url`, `restored_image_base64` (null if not embedded; `auto` embeds only
PNGs <= 3 MiB), `detected_degradations`, `detections{class: probability, threshold, detected}`, `selected_operations[]`
(operation, degradation, parameters, reason), `skipped_operations[]`, `quality_before`, `quality_after`, `quality_change`,
`processing_time_seconds`, `timing_seconds`, `warnings`, `limitations`.
`quality_*` are heuristic image statistics (mean luminance, contrast std, 5-95 % range, Laplacian variance on a 512-px-normalised
copy, noise-sigma estimate, impulse-pixel fraction). They are **not** perceptual quality scores and no PSNR/SSIM is reported for
uploads, because no clean reference exists.

Errors: `{"error": {"code": ..., "message": ...}}` - 400 empty, 413 too large, 415 unsupported/corrupt, 422 invalid
dimensions/truncated data, 503 model artifacts unavailable, 500 internal (no stack trace sent; see server log).
Limits (env / `.env`, see `.env.example`): 25 MiB upload, 8000 px side, 16 MP, 32 px minimum. Uploads are read in 1 MiB chunks and
rejected as soon as the limit is exceeded; decoded format (not extension/Content-Type) decides acceptance; saved files get random
UUID names, client filenames are never used as paths.

## D. Evaluation (classifier and restoration are evaluated separately)
**1. Classifier on synthetic held-out data** - printed by the notebook (per-class precision/recall/F1, micro/macro F1, confusion
matrices, false-alarm rate on clean images). This is performance on *synthetic degradations of held-out source images* only.

**2. Classifier on REAL photos** (the number that matters for deployment): label 100+ real photos yourself in a CSV
(`filename,low_light,low_contrast,gaussian_noise,salt_pepper_noise,blur`), never use them for training/threshold tuning, then
```bat
python evaluation.py classifier --images-dir my_real_photos --labels-csv my_real_photos\labels.csv --out real_report.json
```

**3. Restoration with clean references** - the notebook exports `heldout_test_pairs.zip` (clean + degraded pairs made from TEST-split
source images only, `labels.csv`, `manifest.json` with `"split": "test"`). Unzip it, then
```bat
python evaluation.py restoration --clean-dir pairs\clean --degraded-dir pairs\degraded --labels-csv pairs\labels.csv --manifest pairs\manifest.json --detector labels --out eval_oracle
python evaluation.py restoration --clean-dir pairs\clean --degraded-dir pairs\degraded --labels-csv pairs\labels.csv --manifest pairs\manifest.json --detector model --out eval_model
```
`--detector labels` uses ground truth (isolates restoration quality), `--detector model` uses the trained classifier (end-to-end).
It compares **degraded vs fixed baseline (every operation on every image) vs adaptive** with PSNR, SSIM, per-category tables for
images containing each degradation, improved / worsened / unchanged counts (+-0.05 dB dead zone) and runtime. The manifest check
refuses non-test splits; without a manifest it warns that leakage cannot be verified.

How to read it: PSNR in dB (capped at 50), higher = closer to the clean original (~+1 dB is visible, +0.2 dB marginal); SSIM 0-1.
Both can disagree with human taste (CLAHE can look better but score lower). Blur rows should show ~0 dB gain: sharpening is not
deblurring. If "adaptive worsened" counts are high for `--detector model` but not for `labels`, the classifier is the weak link.

## F. Troubleshooting
* **503 / `model_unavailable`**: `/health` shows the reason (missing file, class-order/version mismatch, hash mismatch). Re-copy all four files from the same notebook run.
* **`ModuleNotFoundError`**: activate the venv (`.venv\Scripts\activate.bat`) and run from the `backend` folder.
* **Port 8000 busy**: `uvicorn main:app --port 8001`.
* **Slow on big images**: non-local-means is CPU-heavy (smaller windows are used above 3 MP). Lower `MAX_PIXELS` in `.env`.
* **Everything flagged / nothing flagged on real photos**: the classifier was trained on synthetic data; run the real-photo evaluation and consider retraining with more realistic degradations (JPEG recompression, real noise/blur).
