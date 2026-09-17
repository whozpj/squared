"""Image preprocessing for OCR (DESIGN.md §4 Phase 1).

Each step is a small function so they can be A/B'd on the eval set. OpenCV/numpy
are imported lazily; `available()` reports whether preprocessing can run.
"""

from __future__ import annotations


def available() -> bool:
    try:
        import cv2  # noqa: F401
        import numpy  # noqa: F401
    except Exception:
        return False
    return True


def _to_gray(img):
    import cv2

    if len(img.shape) == 3:
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return img


def _deskew(gray):
    import cv2
    import numpy as np

    inv = cv2.bitwise_not(gray)
    coords = np.column_stack(np.where(inv > 0))
    if coords.size == 0:
        return gray
    angle = cv2.minAreaRect(coords)[-1]
    angle = -(90 + angle) if angle < -45 else -angle
    if abs(angle) < 0.5:
        return gray
    h, w = gray.shape
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(gray, m, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def _binarize(gray):
    import cv2

    return cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15
    )


def preprocess(image: bytes) -> bytes:
    """Grayscale -> deskew -> upscale -> adaptive threshold -> PNG bytes.

    Falls back to returning the input unchanged if OpenCV isn't available.
    """
    if not available():
        return image

    import cv2
    import numpy as np

    arr = cv2.imdecode(np.frombuffer(image, np.uint8), cv2.IMREAD_COLOR)
    if arr is None:
        return image
    gray = _to_gray(arr)
    gray = _deskew(gray)
    # Upscale small images toward a legible glyph height.
    if gray.shape[0] < 1000:
        scale = 1000 / gray.shape[0]
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    binary = _binarize(gray)
    ok, buf = cv2.imencode(".png", binary)
    return buf.tobytes() if ok else image
