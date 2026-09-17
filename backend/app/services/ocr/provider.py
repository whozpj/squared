"""OCR provider interface + Tesseract implementation (DESIGN.md §4 Phase 5).

The interface keeps OCR swappable (a cloud/LLM provider could be added for
low-confidence receipts later) without touching the parser/reconciler/pipeline.
Tesseract deps are imported lazily so the package imports even when they're absent.
"""

from __future__ import annotations

from typing import Protocol


class OcrProvider(Protocol):
    def extract_text(self, image: bytes) -> str:
        """Return the receipt's text, one logical line per row (top-to-bottom)."""
        ...


class TesseractProvider:
    """Layout-aware Tesseract: uses image_to_data to rebuild lines from word boxes."""

    def __init__(self, psm: int = 6, oem: int = 1) -> None:
        self.config = f"--oem {oem} --psm {psm}"

    def extract_text(self, image: bytes) -> str:
        import io

        import pytesseract
        from PIL import Image

        data = pytesseract.image_to_data(
            Image.open(io.BytesIO(image)),
            config=self.config,
            output_type=pytesseract.Output.DICT,
        )
        return self._lines_from_data(data)

    @staticmethod
    def _lines_from_data(data: dict) -> str:
        # Group words sharing (block, par, line), preserve reading order, join with spaces.
        lines: dict[tuple, list[tuple[int, str]]] = {}
        n = len(data["text"])
        for i in range(n):
            word = (data["text"][i] or "").strip()
            if not word:
                continue
            key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
            lines.setdefault(key, []).append((data["left"][i], word))
        out = []
        for key in sorted(lines):
            words = [w for _, w in sorted(lines[key])]
            out.append(" ".join(words))
        return "\n".join(out)


def is_tesseract_available() -> bool:
    try:
        import pytesseract  # noqa: F401
    except Exception:
        return False
    try:
        import pytesseract

        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False
