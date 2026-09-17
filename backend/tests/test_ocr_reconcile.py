from app.services.ocr.pipeline import parse_receipt_text
from app.services.ocr.reconcile import reconcile
from app.services.ocr.types import ParsedItem, ParsedReceipt


def _receipt(items, subtotal, tax, tip, total):
    return ParsedReceipt(
        items=[ParsedItem(n, p) for n, p in items],
        subtotal=subtotal,
        tax=tax,
        tip=tip,
        total=total,
    )


def test_balanced_receipt_reconciles():
    r = reconcile(_receipt([("a", 1200), ("b", 800)], 2000, 160, 400, 2560))
    assert r.reconciled is True
    assert r.issues == []
    assert r.confidence == 1.0


def test_items_not_matching_subtotal_is_flagged():
    r = reconcile(_receipt([("a", 1200), ("b", 700)], 2000, 0, 0, 2000))
    assert r.reconciled is False
    assert any("items sum" in i for i in r.issues)
    assert r.confidence < 1.0


def test_total_mismatch_is_flagged_not_repaired():
    r = reconcile(_receipt([("a", 1000)], 1000, 100, 0, 9999))
    assert r.reconciled is False
    # Values are left untouched — no silent repair.
    assert r.total == 9999
    assert r.subtotal == 1000


def test_missing_totals_flagged():
    r = reconcile(ParsedReceipt(items=[ParsedItem("a", 500)]))
    assert r.reconciled is False


def test_end_to_end_text_reconciles():
    text = "Burger 12.00\nFries 4.50\nSubtotal 16.50\nTax 1.00\nTotal 17.50\n"
    r = parse_receipt_text(text)
    assert r.reconciled is True
    assert r.total == 1750
