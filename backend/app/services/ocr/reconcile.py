"""Reconciliation engine (DESIGN.md §4 Phase 3) — the reliability guarantee.

Checks the numbers add up. It NEVER edits values to force a balance (no silent
repair): if a receipt can't be reconciled it is flagged low-confidence and routed
to manual review, so Squared never emits numbers that don't add up.
"""

from __future__ import annotations

from app.services.ocr.types import ParsedReceipt

DEFAULT_TOLERANCE = 1  # cents


def reconcile(receipt: ParsedReceipt, tolerance: int = DEFAULT_TOLERANCE) -> ParsedReceipt:
    issues: list[str] = []
    items_sum = sum(i.price for i in receipt.items)

    if not receipt.items:
        issues.append("no line items detected")

    if receipt.subtotal is not None and abs(items_sum - receipt.subtotal) > tolerance:
        issues.append(f"items sum {items_sum} != subtotal {receipt.subtotal}")

    if receipt.total is not None:
        base = receipt.subtotal if receipt.subtotal is not None else items_sum
        expected = base + (receipt.tax or 0) + (receipt.tip or 0)
        if abs(expected - receipt.total) > tolerance:
            issues.append(f"subtotal+tax+tip {expected} != total {receipt.total}")

    if receipt.subtotal is None and receipt.total is None:
        issues.append("no subtotal or total detected")

    receipt.issues = issues
    receipt.reconciled = not issues
    # Confidence: full when it balances, degraded per issue. OCR word-confidence (if
    # the provider supplies it) can be folded in later; text-only defaults to structural.
    receipt.confidence = 1.0 if not issues else max(0.0, 1.0 - 0.34 * len(issues))
    return receipt
