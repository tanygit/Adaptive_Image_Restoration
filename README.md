# Adaptive Image Restoration

An adaptive computer vision studio that detects five distinct types of image degradation using a deep CNN classifier and applies explainable, deterministic OpenCV pipelines to restore clarity.

**Supported degradations:** low light, low contrast, Gaussian noise, salt-and-pepper noise, and soft blur (including simultaneous multi-degradation combinations).

---

## Features

- **Pop-Art / Risograph Web Studio:** High-contrast, tactile UI with vibrant spot colors, newsprint grain, and halftone dot textures.
- **Interactive Before/After Comparison:** Smooth split-curtain slider and side-by-side view with keyboard scrubbing (`←` / `→`, `Home` / `End`) and instant hold-to-peek (`Spacebar` or `\`).
- **Explainable CV Diagnostics:** Transparent metrics drawer reporting exact quality deltas (brightness, contrast std dev, Laplacian sharpness variance, estimated noise σ) and pipeline execution latencies.
- **Adjustable Restoration Strength:** Toggle between `Gentle`, `Balanced`, and `Strong` presets with instant re-processing.
- **1-Click Test Presets:** Built-in synthetic test samples (*Low-Light Sunset*, *Blurry Street*, *Grainy Frame*) for instant evaluation without uploading external files.
- **Power-User Ergonomics:** Global clipboard paste (`Ctrl + V`), 25 MiB client-side upload validation, and direct high-resolution PNG download.

---

## Project Structure

```text
Adaptive_Image_Restoration/
├── .agent/                  # Impeccable skill and design toolchain
├── DESIGN.md                # Design system specification and color tokens
├── README.md
├── frontend/                # React 18 + Vite 5 + Tailwind CSS Studio
│   ├── index.html
│   ├── package.json
│   ├── tailwind.config.js
│   ├── vite.config.js
│   └── src/
│       ├── App.jsx
│       ├── main.jsx
│       ├── index.css
│       └── components/
│           ├── Header.jsx
│           ├── DropZone.jsx
│           ├── ComparisonSlider.jsx
│           ├── ControlDeck.jsx
│           ├── DiagnosticsDrawer.jsx
│           └── BackgroundArtwork.jsx
└── backend/                 # FastAPI REST API + OpenCV Pipelines + PyTorch CNN
    ├── main.py              # API server and routing
    ├── config.py            # Environment configurations & limits
    ├── degradation_model.py # PyTorch CNN classifier definition
    ├── pipeline.py          # Adaptive OpenCV restoration chain
    ├── requirements.txt     # Python production dependencies
    ├── artifacts/           # Trained model weights & threshold configs
    ├── test_images/         # Local test images
    └── tests/               # Backend unit and plumbing tests
```

---

## Quickstart: Running Backend & Frontend

To run the complete application, open **two terminal windows**: one for the backend and one for the frontend.

### Terminal 1: Backend (FastAPI)

1. Navigate to the `backend` folder:
   ```powershell
   cd backend
   ```

2. Create and activate a Python virtual environment:
   - **PowerShell (Windows):**
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
     *(If script execution is disabled on PowerShell, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first).*
   - **Command Prompt (CMD):**
     ```bat
     python -m venv .venv
     .venv\Scripts\activate.bat
     ```

3. Install requirements:
   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```
   > *Tip: If you encounter low-space (`ENOSPC`) issues on your primary drive, redirect pip cache: `pip install --cache-dir "D:\pip-cache" -r requirements.txt`.*

4. Ensure model artifacts exist in `backend/artifacts/`:
   - `degradation_cnn.pth`
   - `class_thresholds.json`
   - `restoration_config.json`
   - `training_metadata.json`

5. Start the FastAPI server:
   ```powershell
   python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
   ```

   - API Documentation: http://127.0.0.1:8000/docs
   - Health check: http://127.0.0.1:8000/health

---

### Terminal 2: Frontend (React + Vite)

1. Navigate to the `frontend` folder:
   ```powershell
   cd frontend
   ```

2. Install Node dependencies:
   ```powershell
   npm install --legacy-peer-deps
   ```

3. Start the Vite development server:
   ```powershell
   npm run dev
   ```

4. Open your browser and navigate to:
   👉 **http://localhost:5173**

---

## CLI Test Client (Optional)

You can also test the restoration pipeline directly from the command line without the web browser:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python client_example.py test_images\photo.jpg --strength balanced --out restored.png --open
```

Replace `photo.jpg` with any degraded test photo in `backend/test_images/`.

---

## Running Automated Tests

Run backend unit tests to verify OpenCV operations and endpoint plumbing:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m pytest -q
```

---

## API Endpoints Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Verifies service status and whether model artifacts are loaded |
| `GET` | `/docs` | Swagger / OpenAPI interactive documentation |
| `POST` | `/restore` | Uploads an image (`multipart/form-data`) and runs adaptive restoration |
| `GET` | `/restored/{request_id}` | Retrieves a cached restored image by ID |

**Supported Upload Formats:** JPEG, PNG, WebP (up to 25 MiB).  
**Strength Options:** `gentle`, `balanced`, `strong`.

---

## Scientific Considerations & Constraints

- **Explainable Operations:** All image modifications are carried out by deterministic OpenCV filters (CLAHE, bilateral filters, unsharp masking, median filtering).
- **Blur Boundaries:** Soft motion or lens blur is sharpened using conservative unsharp masking; it does **not** hallucinate generative textures or claim true blind-deconvolution reconstruction.
