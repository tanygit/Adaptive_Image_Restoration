# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

delegated: React + Vite + Tailwind CSS (running on port 5173, aligned with backend CORS configuration in `backend/main.py`)

## Users

Everyday users, students, and photo enthusiasts dealing with degraded digital photographs (underexposed/low-light, washed out/low-contrast, grainy/noisy, or slightly blurry) who need an effortless, one-click tool to restore visual clarity without complex photo-editing software.

## Product Purpose

Provide an accessible, transparent web interface for adaptive image restoration. A lightweight CNN detects specific image flaws, and targeted, deterministic OpenCV operations restore the image based on detected degradations and a user-selected restoration strength (`gentle`, `balanced`, or `strong`). Success is defined by noticeable visual enhancement, immediate before/after comparison, and fast, seamless processing.

## Positioning

Explainable, deterministic restoration rather than black-box AI hallucination. It pairs deep learning classification with classic computer vision: the neural network diagnoses the defects, while proven OpenCV algorithms fix them without fabricating synthetic details.

## Operating Context

Modern desktop and mobile web browsers communicating with a local FastAPI backend server (`http://127.0.0.1:8000`). Standard flow consists of uploading an image (JPEG, PNG, WebP), automatic analysis and restoration, comparing results interactively, and downloading the restored PNG.

## Capabilities and Constraints

- **Degradation Detection**: Identifies 5 specific categories: Low Light, Low Contrast, Gaussian Noise, Salt & Pepper Noise, and Blur.
- **Restoration Modes**: Offers `gentle`, `balanced` (default), and `strong` processing presets.
- **Visual Presentation**: Interactive split-screen slider / side-by-side view with visual degradation badges and before/after quality metrics.
- **Constraints**:
  - Image size and dimension boundaries enforced by backend configuration.
  - Blur recovery uses conservative sharpening; does not synthesize lost high-frequency details.
  - Restoration artifacts expire based on backend TTL.

## Evidence on Hand

- Fully functional FastAPI backend service in [backend/main.py](backend/main.py).
- Pre-trained CNN weights and configuration artifacts in [backend/artifacts/](backend/artifacts/):
  - `degradation_cnn.pth`
  - `class_thresholds.json`
  - `restoration_config.json`
  - `training_metadata.json`
- Test image collection available in [backend/test_images/](backend/test_images/).

## Product Principles

1. **Honest Restoration**: Accurately disclose detected issues and applied filters; avoid claiming generative hallucination as true detail recovery.
2. **Immediate Visual Impact**: Anchor the experience around an intuitive before/after comparison slider so users immediately evaluate results.
3. **Frictionless Workflow**: Default to sensible automated settings so users can upload and restore in seconds, while keeping technical metrics easily inspectable.
4. **Resilient Feedback**: Provide clear upload progress, informative warnings when images are clean or overly compressed, and actionable error handling.

