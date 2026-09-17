from app.services.ocr.eval import score
from app.services.ocr.pipeline import parse_receipt_text


def test_scorer_perfect_match():
    text = "A 10.00\nB 5.00\nSubtotal 15.00\nTax 1.00\nTotal 16.00\n"
    pred = parse_receipt_text(text)
    truth = {
        "items": [{"name": "A", "price": 1000}, {"name": "B", "price": 500}],
        "subtotal": 1500,
        "tax": 100,
        "total": 1600,
    }
    s = score(pred, truth)
    assert s["item_f1"] == 1.0
    assert s["field_accuracy"] == 1.0
    assert s["reconciled"] is True


def test_scorer_penalizes_missing_item():
    pred = parse_receipt_text("A 10.00\nSubtotal 10.00\nTotal 10.00\n")
    truth = {
        "items": [{"name": "A", "price": 1000}, {"name": "B", "price": 500}],
        "subtotal": 1500,
        "total": 1500,
    }
    s = score(pred, truth)
    assert s["item_recall"] < 1.0
    assert s["field_accuracy"] < 1.0
