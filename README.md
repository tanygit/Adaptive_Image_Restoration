# Adaptive Image Restoration

An image-restoration project that detects five types of image
degradation using a small CNN and applies explainable OpenCV operations
to restore the image.

**Supported degradations:** low light, low contrast, Gaussian noise,
salt-and-pepper noise, and blur (including combinations).

## How it works

1.  Upload a degraded image.
2.  The CNN predicts which degradations are present.
3.  The backend applies matching OpenCV restoration operations.
4.  The API returns the restored image, detected degradations,
    applied/skipped operations, and diagnostic statistics.

> **Important:** Trained model artifacts and training file are not included in this.

## Project structure

``` text
adaptive_restoration/
├── .gitignore
├── README.md
├── frontend/
└── backend/
    ├── main.py
    ├── requirements-dev.txt
    ├── client_example.py
    ├── artifacts/
    ├── restored_images/
    ├── test_images/
    └── tests/
```

## Setup (Windows)

Open **Command Prompt** in the project root:

``` bat
cd backend
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Python 3.11 is recommended (64-bit Python 3.10--3.12 is supported). 

## Add trained artifacts

After Training copy these four files into `backend/artifacts/`:

-   `degradation_cnn.pth`
-   `class_thresholds.json`
-   `restoration_config.json`
-   `training_metadata.json`

Keep all four files from the **same notebook run**.

## Run the backend

From the `backend` folder, with the virtual environment activated:

``` bat
uvicorn main:app --host 127.0.0.1 --port 8000
```

Open these URLs in your browser:

-   API documentation: http://127.0.0.1:8000/docs
-   Health check: http://127.0.0.1:8000/health

You can also place a test image in `backend/test_images/` and run this
in a second terminal:

``` bat
cd backend
.venv\Scripts\activate.bat
python client_example.py test_images\photo.jpg --strength balanced --out restored.png --open
```

Replace `photo.jpg` with your image filename.

## API endpoints

-   `GET /health` --- checks whether the model artifacts are available.
-   `GET /docs` --- interactive API documentation.
-   `POST /restore` --- upload an image for restoration.
-   `GET /restored/{request_id}` --- download a restored PNG while it is
    available.

Restoration strength can be `gentle`, `balanced`, or `strong`. The API
accepts JPEG, PNG, and WebP images.

## Run tests

From the `backend` folder, with the virtual environment activated:

``` bat
python -m pytest -q
```

These tests check the backend plumbing and do not require the trained
artifacts.

## Notes

-   The backend uses a CNN for degradation detection and OpenCV
    operations for restoration.
-   Blur handling uses conservative sharpening; it does **not** claim to
    recover lost detail through true deblurring.
-   Uploaded images are subject to configured size and dimension limits.
    See `backend/.env.example` for available settings.
