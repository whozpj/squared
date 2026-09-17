"""OCR pipeline: image bytes -> (raw & preprocessed) Tesseract -> parse -> reconcile.

We OCR more than one image variant and let reconciliation choose the winner: clean
digital images read best raw, while messy photos need preprocessing. Picking the
variant that actually reconciles is what makes the pipeline robust across both.

This is the seam the async OcrJob worker (DESIGN.md §4) will call. The provider is
injectable so tests can feed canned OCR text without needing the Tesseract binary.
"""

from __future__ import annotations

from app.services.ocr.parser import parse_text
from app.services.ocr.preprocess import available as preprocess_available
from app.services.ocr.preprocess import preprocess
from app.services.ocr.provider import OcrProvider, TesseractProvider
from app.services.ocr.reconcile import reconcile
from app.services.ocr.types import ParsedReceipt


def parse_receipt_text(text: str) -> ParsedReceipt:
    """Text -> structured, reconciled receipt (no image needed)."""
    return reconcile(parse_text(text))


def _score(r: ParsedReceipt) -> tuple:
    # Prefer a receipt that reconciles, then higher confidence, then more items.
    return (1 if r.reconciled else 0, r.confidence, len(r.items))


def run_pipeline(
    image: bytes,
    provider: OcrProvider | None = None,
    do_preprocess: bool = True,
) -> ParsedReceipt:
    """Full image -> reconciled receipt, choosing the best-reconciling variant."""
    provider = provider or TesseractProvider()

    variants: list[bytes] = [image]
    if do_preprocess and preprocess_available():
        prepared = preprocess(image)
        if prepared != image:
            variants.append(prepared)

    best: ParsedReceipt | None = None
    for variant in variants:
        candidate = parse_receipt_text(provider.extract_text(variant))
        if best is None or _score(candidate) > _score(best):
            best = candidate
    return best if best is not None else ParsedReceipt()
