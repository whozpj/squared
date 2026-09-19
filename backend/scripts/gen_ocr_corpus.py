"""Generate a labeled synthetic receipt corpus to benchmark the OCR pipeline.

Renders receipts with known ground truth, then applies real-world degradations
(skew, blur, sensor noise, thermal fade, JPEG artifacts) so the accuracy number
reflects robustness, not just clean text. Ground truth is exact by construction.

Usage:  python scripts/gen_ocr_corpus.py <out_dir> [count]
Then:   python -m app.services.ocr.eval <out_dir>

The corpus is NOT committed (see .gitignore); regenerate it anytime.
"""

from __future__ import annotations

import io
import json
import random
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONTS = [
    "/System/Library/Fonts/Menlo.ttc",
    "/System/Library/Fonts/Supplemental/Courier New.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]
ITEMS = [
    "Cheeseburger", "Fries", "Caesar Salad", "Ribeye Steak", "Grilled Salmon",
    "Margherita Pizza", "Pad Thai", "Iced Latte", "Draft Beer", "House Wine",
    "Spring Rolls", "Miso Soup", "Chicken Wings", "Nachos", "Espresso",
    "Tiramisu", "Cheesecake", "Lemonade", "Club Sandwich", "Fish Tacos",
]
MERCHANTS = ["JOE'S DINER", "THE LAKESIDE", "URBAN KITCHEN", "CORNER CAFE", "BLUE OAK GRILL"]


def _font(size: int):
    for path in FONTS:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default(size=size)


def make_receipt(rng: random.Random) -> tuple[dict, list[tuple[str, int]]]:
    n = rng.randint(2, 7)
    items = []
    for _ in range(n):
        name = rng.choice(ITEMS)
        price = rng.randint(300, 4800)
        items.append({"name": name, "price": price})
    subtotal = sum(i["price"] for i in items)
    tax = round(subtotal * rng.choice([0.07, 0.08, 0.0875, 0.10]))
    tip = round(subtotal * rng.choice([0.0, 0.15, 0.18, 0.20]))
    total = subtotal + tax + tip
    truth = {"items": items, "subtotal": subtotal, "tax": tax, "tip": tip, "total": total}

    lines: list[tuple[str, int]] = [(rng.choice(MERCHANTS), 0), ("", 0)]
    for it in items:
        lines.append((it["name"], it["price"]))
    lines.append(("", 0))
    lines.append(("SUBTOTAL", subtotal))
    if tax:
        lines.append(("TAX", tax))
    if tip:
        lines.append(("TIP", tip))
    lines.append(("TOTAL", total))
    return truth, lines


def render(lines: list[tuple[str, int]], rng: random.Random) -> Image.Image:
    font = _font(rng.randint(30, 40))
    width = rng.randint(560, 720)
    row_h = font.size + 16
    img = Image.new("RGB", (width, 60 + row_h * len(lines)), "white")
    d = ImageDraw.Draw(img)
    y = 30
    for label, price in lines:
        if label:
            d.text((36, y), label, fill="black", font=font)
        if price:
            amount = f"{price/100:.2f}"
            w = d.textlength(amount, font=font)
            d.text((width - 36 - w, y), amount, fill="black", font=font)
        y += row_h
    return img


def degrade(img: Image.Image, rng: random.Random, hard: bool) -> bytes:
    arr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    if hard:
        # Skew
        angle = rng.uniform(-3.5, 3.5)
        h, w = arr.shape[:2]
        m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
        arr = cv2.warpAffine(arr, m, (w, h), borderValue=(255, 255, 255))
        # Blur
        k = rng.choice([1, 3, 3, 5])
        if k > 1:
            arr = cv2.GaussianBlur(arr, (k, k), 0)
        # Thermal fade (lower contrast, warm tint)
        arr = cv2.convertScaleAbs(arr, alpha=rng.uniform(0.75, 0.95), beta=rng.uniform(5, 30))
        # Sensor noise
        noise = np.random.normal(0, rng.uniform(4, 14), arr.shape).astype(np.int16)
        arr = np.clip(arr.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    ok, buf = cv2.imencode(".jpg", arr, [cv2.IMWRITE_JPEG_QUALITY, rng.randint(55, 92) if hard else 95])
    return buf.tobytes() if ok else io.BytesIO().getvalue()


def main(out_dir: str, count: int) -> None:
    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)
    rng = random.Random(1234)
    for i in range(count):
        hard = i >= count // 2  # first half clean, second half degraded
        truth, lines = make_receipt(rng)
        img = render(lines, rng)
        data = degrade(img, rng, hard)
        stem = f"{'hard' if hard else 'clean'}_{i:02d}"
        (root / f"{stem}.jpg").write_bytes(data)
        (root / f"{stem}.json").write_text(json.dumps(truth))
    print(f"wrote {count} receipts to {root} ({count//2} clean, {count-count//2} degraded)")


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "ocr_corpus"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    main(out, n)
