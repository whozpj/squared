"""Real end-to-end OCR: render a receipt image, read it back through Tesseract.

Skipped automatically if the vision deps or the tesseract binary aren't present.
"""

import io

import pytest

from app.services.ocr.preprocess import available as cv2_available
from app.services.ocr.provider import is_tesseract_available

pytestmark = pytest.mark.skipif(
    not (cv2_available() and is_tesseract_available()),
    reason="requires opencv + tesseract binary",
)


def _render_receipt() -> bytes:
    from PIL import Image, ImageDraw, ImageFont

    lines = [
        "JOE'S DINER",
        "",
        "BURGER          12.00",
        "FRIES            4.50",
        "SODA             2.50",
        "SUBTOTAL        19.00",
        "TAX              1.52",
        "TIP              3.80",
        "TOTAL           24.32",
    ]
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 34)
    except Exception:
        font = ImageFont.load_default(size=34)

    img = Image.new("RGB", (640, 60 + 46 * len(lines)), "white")
    draw = ImageDraw.Draw(img)
    y = 30
    for line in lines:
        draw.text((40, y), line, fill="black", font=font)
        y += 46
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_full_pipeline_reads_and_reconciles():
    from app.services.ocr.pipeline import run_pipeline

    receipt = run_pipeline(_render_receipt())
    assert receipt.total == 2432, receipt.to_dict()
    assert receipt.subtotal == 1900, receipt.to_dict()
    assert len(receipt.items) >= 3, receipt.to_dict()
    assert receipt.reconciled is True, receipt.issues
