"""OCR eval harness (DESIGN.md §4 Phase 0) — "prove it works" with numbers.

Corpus layout (not committed; large images live outside git):
    corpus/<name>.png      # or .jpg
    corpus/<name>.json     # ground truth: {items:[{name,price}], subtotal, tax, tip, total}

Run:  python -m app.services.ocr.eval path/to/corpus
Scores item precision/recall/F1, field accuracy, and reconciliation pass-rate.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from app.services.ocr.types import ParsedReceipt


def _price_multiset(items: list[dict]) -> list[int]:
    return sorted(int(i["price"]) for i in items)


def score(pred: ParsedReceipt, truth: dict, price_tol: int = 1) -> dict:
    """Compare one prediction to ground truth. Item match is by price (order-free)."""
    pred_prices = sorted(i.price for i in pred.items)
    true_prices = _price_multiset(truth.get("items", []))

    # Greedy multiset match within tolerance.
    remaining = true_prices.copy()
    matched = 0
    for p in pred_prices:
        for j, t in enumerate(remaining):
            if abs(p - t) <= price_tol:
                matched += 1
                remaining.pop(j)
                break
    precision = matched / len(pred_prices) if pred_prices else (1.0 if not true_prices else 0.0)
    recall = matched / len(true_prices) if true_prices else 1.0
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)

    fields = ["subtotal", "tax", "tip", "total"]
    field_hits = sum(
        1 for f in fields if truth.get(f) is not None and getattr(pred, f) == truth.get(f)
    )
    field_total = sum(1 for f in fields if truth.get(f) is not None)
    field_acc = field_hits / field_total if field_total else 1.0

    return {
        "item_precision": round(precision, 3),
        "item_recall": round(recall, 3),
        "item_f1": round(f1, 3),
        "field_accuracy": round(field_acc, 3),
        "reconciled": pred.reconciled,
    }


def run_eval(corpus_dir: str) -> dict:
    from app.services.ocr.pipeline import run_pipeline  # local import: needs vision deps

    root = Path(corpus_dir)
    results = []
    for img in sorted([*root.glob("*.png"), *root.glob("*.jpg")]):
        truth_path = img.with_suffix(".json")
        if not truth_path.exists():
            continue
        truth = json.loads(truth_path.read_text())
        pred = run_pipeline(img.read_bytes())
        s = score(pred, truth)
        s["name"] = img.name
        results.append(s)

    if not results:
        print("no labeled receipts found in", corpus_dir)
        return {"count": 0}

    def avg(k: str) -> float:
        return round(sum(r[k] for r in results) / len(results), 3)

    summary = {
        "count": len(results),
        "item_f1": avg("item_f1"),
        "field_accuracy": avg("field_accuracy"),
        "reconciled_rate": round(sum(1 for r in results if r["reconciled"]) / len(results), 3),
    }
    print(json.dumps({"summary": summary, "per_receipt": results}, indent=2))
    return summary


if __name__ == "__main__":
    run_eval(sys.argv[1] if len(sys.argv) > 1 else "corpus")
