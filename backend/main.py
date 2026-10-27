"""
main.py - FastAPI service: upload -> validate -> detect degradations -> restore -> diagnostics.

Run from this folder:   uvicorn main:app --host 127.0.0.1 --port 8000
Interactive docs:        http://127.0.0.1:8000/docs
"""
from __future__ import annotations

import asyncio
import base64
import logging
import re
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, List, Literal, Optional

import cv2
import numpy as np
from fastapi import FastAPI, File, Query, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import Settings, load_settings
from image_io import ImageValidationError, decode_image, sanitize_filename
from image_quality import STATS_DISCLAIMER, compute_quality_stats
from model import (ANALYSIS_MAX_SIDE, CLASS_NAMES, MODEL_VERSION, RESTORATION_CONFIG_FILE, ArtifactError,
                   DegradationPredictor)
from restoration import STRENGTHS, Restorer, load_config

logger = logging.getLogger("adaptive_restoration")
API_VERSION = "1.0.0"
MULTIPART_OVERHEAD_BYTES = 1024 * 1024
RESTORED_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")

STATIC_LIMITATIONS = [
    "The degradation classifier was trained on SYNTHETIC degradations; accuracy on real photographs must be "
    "validated separately and may be lower.",
    "No clean reference exists for an uploaded image, so PSNR/SSIM are not computed here. Reported statistics are "
    "heuristics, not perceptual-quality scores.",
    "Blur is handled with conservative sharpening only; lost detail cannot be recovered.",
]


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


# ------------------------------------------------------------------ response models
class Detection(BaseModel):
    probability: float
    threshold: float
    detected: bool


class AppliedOperation(BaseModel):
    operation: str
    degradation: str
    parameters: Dict[str, object]
    reason: str


class SkippedOperation(BaseModel):
    degradation: str
    reason: str


class RestoreResponse(BaseModel):
    request_id: str
    filename: str
    strength: Literal["gentle", "balanced", "strong"]
    restored_image_url: str
    restored_image_base64: Optional[str] = None
    restored_image_media_type: str = "image/png"
    detected_degradations: List[str]
    detections: Dict[str, Detection]
    selected_operations: List[AppliedOperation]
    skipped_operations: List[SkippedOperation]
    quality_before: Dict[str, float]
    quality_after: Dict[str, float]
    quality_change: Dict[str, float]
    quality_notes: str
    processing_time_seconds: float
    timing_seconds: Dict[str, float]
    warnings: List[str]
    limitations: List[str]


# ------------------------------------------------------------------ helpers
def cleanup_restored_files(directory: Path, ttl_seconds: int) -> None:
    """Delete restored PNGs older than the TTL so the folder cannot grow without bound."""
    cutoff = time.time() - ttl_seconds
    for path in directory.glob("*.png"):
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
        except OSError as exc:
            logger.warning("Could not remove old restored file %s: %s", path.name, exc)


async def read_upload_limited(upload: UploadFile, limit: int) -> bytes:
    """Read the upload in chunks and stop as soon as it exceeds the limit (never buffers unbounded data)."""
    chunks, total = [], 0
    while True:
        chunk = await upload.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise ApiError(413, "file_too_large", f"The file exceeds the {limit / (1024 * 1024):.0f} MiB upload limit.")
        chunks.append(chunk)
    return b"".join(chunks)


def encode_png(img_rgb: np.ndarray) -> bytes:
    ok, buf = cv2.imencode(".png", cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_PNG_COMPRESSION, 3])
    if not ok:
        raise RuntimeError("PNG encoding failed")
    return buf.tobytes()


def process_image(app: FastAPI, settings: Settings, data: bytes, filename: str, strength: str,
                  response_image: str) -> RestoreResponse:
    """Blocking, CPU-bound pipeline; executed in a worker thread."""
    t_start = time.perf_counter()
    img, warnings, _ = decode_image(data, settings.max_image_side, settings.min_image_side, settings.max_pixels)
    before = compute_quality_stats(img)
    t_stats = time.perf_counter()

    detections = app.state.predictor.predict(img)
    t_cls = time.perf_counter()
    detected_names = [n for n in CLASS_NAMES if detections[n]["detected"]]
    if max(img.shape[:2]) > ANALYSIS_MAX_SIDE:
        warnings.append(f"Image was analysed after shrinking its longer side to {ANALYSIS_MAX_SIDE}px; very fine noise "
                        "or blur may be under-detected.")

    result = app.state.restorer.restore(img, {n: detections[n]["detected"] for n in CLASS_NAMES}, strength)
    t_res = time.perf_counter()
    warnings.extend(result.warnings)
    if not detected_names:
        warnings.append("No degradation exceeded its threshold; the image was returned unchanged.")

    after = compute_quality_stats(result.image)
    change = {k: round(after[k] - before[k], 4) for k in before if k not in ("width", "height", "megapixels")}

    png = encode_png(result.image)
    request_id = uuid.uuid4().hex
    (settings.restored_dir / f"{request_id}.png").write_bytes(png)
    include_b64 = response_image == "base64" or (response_image == "auto" and len(png) <= settings.inline_base64_max_bytes)
    t_end = time.perf_counter()
    return RestoreResponse(
        request_id=request_id, filename=filename, strength=strength,  # type: ignore[arg-type]
        restored_image_url=f"/restored/{request_id}",
        restored_image_base64=base64.b64encode(png).decode("ascii") if include_b64 else None,
        detected_degradations=detected_names,
        detections={n: Detection(**detections[n]) for n in CLASS_NAMES},
        selected_operations=[AppliedOperation(**op) for op in result.operations],
        skipped_operations=[SkippedOperation(**s) for s in result.skipped],
        quality_before=before, quality_after=after, quality_change=change,
        quality_notes=STATS_DISCLAIMER,
        processing_time_seconds=round(t_end - t_start, 4),
        timing_seconds={"decode_and_stats": round(t_stats - t_start, 4), "classification": round(t_cls - t_stats, 4),
                        "restoration": round(t_res - t_cls, 4), "encode_and_save": round(t_end - t_res, 4)},
        warnings=warnings, limitations=STATIC_LIMITATIONS)


# ------------------------------------------------------------------ application
def create_app(settings: Optional[Settings] = None) -> FastAPI:
    cfg = settings or load_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
        cfg.restored_dir.mkdir(parents=True, exist_ok=True)
        app.state.settings = cfg
        app.state.predictor = None
        app.state.model_error = None
        app.state.restorer = None
        app.state.semaphore = asyncio.Semaphore(cfg.max_concurrent_jobs)
        try:  # weights are loaded ONCE here, not per request
            app.state.predictor = DegradationPredictor(cfg.artifacts_dir, cfg.device)
            app.state.restorer = Restorer(load_config(cfg.artifacts_dir / RESTORATION_CONFIG_FILE))
            logger.info("Model loaded on %s", app.state.predictor.device)
        except (ArtifactError, ValueError) as exc:
            app.state.model_error = str(exc)
            logger.error("Model artifacts unavailable: %s", exc)
        yield

    app = FastAPI(
        title="Adaptive Image Restoration API", version=API_VERSION, lifespan=lifespan,
        description="Detects multiple degradations (low light, low contrast, Gaussian noise, salt-and-pepper noise, blur) "
                    "in a single uploaded image and applies a matching classical restoration pipeline.")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.middleware("http")
    async def reject_oversized_requests(request: Request, call_next):
        declared = request.headers.get("content-length")
        if request.url.path == "/restore" and declared and declared.isdigit() \
                and int(declared) > cfg.max_upload_bytes + MULTIPART_OVERHEAD_BYTES:
            return JSONResponse(status_code=413, content={"error": {
                "code": "file_too_large", "message": f"Request body exceeds the {cfg.max_upload_bytes} byte limit."}})
        return await call_next(request)

    @app.exception_handler(ApiError)
    async def api_error_handler(_: Request, exc: ApiError):
        return JSONResponse(status_code=exc.status, content={"error": {"code": exc.code, "message": exc.message}})

    @app.exception_handler(ImageValidationError)
    async def image_error_handler(_: Request, exc: ImageValidationError):
        return JSONResponse(status_code=exc.status, content={"error": {"code": exc.code, "message": exc.message}})

    @app.exception_handler(Exception)
    async def unexpected_error_handler(_: Request, exc: Exception):
        logger.exception("Unhandled error")  # details stay in the server log only
        return JSONResponse(status_code=500, content={"error": {
            "code": "internal_error", "message": "An internal error occurred while processing the request."}})

    @app.get("/", summary="API information")
    def root():
        return {"name": "Adaptive Image Restoration API", "version": API_VERSION, "model_version": MODEL_VERSION,
                "degradation_classes": CLASS_NAMES, "restoration_strengths": list(STRENGTHS),
                "endpoints": {"health": "GET /health", "restore": "POST /restore (multipart field 'file')",
                              "download": "GET /restored/{request_id}", "docs": "GET /docs"}}

    @app.get("/health", summary="Service and model health")
    def health():
        loaded = app.state.predictor is not None
        body = {"status": "ok" if loaded else "degraded", "model_loaded": loaded, "model_version": MODEL_VERSION,
                "device": str(app.state.predictor.device) if loaded else None, "class_names": CLASS_NAMES,
                "thresholds": app.state.predictor.thresholds if loaded else None,
                "artifacts_dir": cfg.artifacts_dir.name, "error": app.state.model_error,
                "limits": {"max_upload_bytes": cfg.max_upload_bytes, "max_image_side": cfg.max_image_side,
                           "max_pixels": cfg.max_pixels}}
        return JSONResponse(status_code=200 if loaded else 503, content=body)

    @app.post("/restore", response_model=RestoreResponse, summary="Detect degradations and restore an image")
    async def restore(
        file: UploadFile = File(..., description="JPEG, PNG or WebP image"),
        strength: Optional[Literal["gentle", "balanced", "strong"]] = Query(None, description="Restoration strength"),
        response_image: Literal["auto", "base64", "url"] = Query(
            "auto", description="'auto' embeds base64 only for small results; 'url' never embeds; 'base64' always embeds"),
    ):
        if app.state.predictor is None or app.state.restorer is None:
            raise ApiError(503, "model_unavailable", f"Model artifacts are not available: {app.state.model_error}")
        data = await read_upload_limited(file, cfg.max_upload_bytes)
        cleanup_restored_files(cfg.restored_dir, cfg.restored_ttl_seconds)
        chosen = strength or app.state.restorer.default_strength
        async with app.state.semaphore:
            return await run_in_threadpool(process_image, app, cfg, data, sanitize_filename(file.filename), chosen,
                                           response_image)

    @app.get("/restored/{request_id}", summary="Download a restored PNG", response_class=FileResponse)
    def download(request_id: str):
        if not RESTORED_ID_PATTERN.fullmatch(request_id):  # only 32 hex chars: no path traversal is possible
            raise ApiError(404, "not_found", "No such restored image.")
        path = cfg.restored_dir / f"{request_id}.png"
        if not path.is_file():
            raise ApiError(404, "not_found", "No such restored image (it may have expired).")
        return FileResponse(path, media_type="image/png", filename=f"restored_{request_id[:8]}.png")

    return app


app = create_app()
