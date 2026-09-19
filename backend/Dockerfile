FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# tesseract for OCR; libgl/libglib for opencv-python-headless.
RUN apt-get update && apt-get install -y --no-install-recommends \
      tesseract-ocr \
      libgl1 \
      libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Run migrations, then serve. Single worker: the in-process WebSocket manager and
# APScheduler require workers=1 (see DESIGN §2).
CMD alembic upgrade head && \
    uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
