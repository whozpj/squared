from app.services.ocr.parser import parse_money, parse_text

CLEAN = """\
Joe's Diner
123 Main St

Cheeseburger      12.00
Fries              4.50
Soda               2.50
Subtotal          19.00
Tax                1.52
Tip                3.80
Total             24.32
VISA ************1234
THANK YOU!
"""


def test_parse_money_basic():
    assert parse_money("12.00") == 1200
    assert parse_money("$1,234.56") == 123456
    assert parse_money("4.50") == 450


def test_parse_money_fixes_ocr_confusions():
    assert parse_money("l2.5O") == 1250  # l->1, O->0
    assert parse_money("S.00") == 500  # S->5
    assert parse_money("B.25") == 825  # B->8


def test_parse_money_negative_markers():
    assert parse_money("5.00-") == -500
    assert parse_money("5.00 CR") == -500


def test_parse_money_rejects_non_money():
    assert parse_money("hello") is None
    assert parse_money("12") is None  # bare integer isn't a price


def test_parse_clean_receipt():
    r = parse_text(CLEAN)
    assert [(i.name, i.price) for i in r.items] == [
        ("Cheeseburger", 1200),
        ("Fries", 450),
        ("Soda", 250),
    ]
    assert r.subtotal == 1900
    assert r.tax == 152
    assert r.tip == 380
    assert r.total == 2432


def test_noise_and_cards_excluded():
    r = parse_text(CLEAN)
    names = [i.name for i in r.items]
    assert not any("VISA" in n.upper() or "THANK" in n.upper() for n in names)


def test_subtotal_not_confused_with_total():
    r = parse_text("Subtotal 10.00\nTotal 11.00\n")
    assert r.subtotal == 1000
    assert r.total == 1100


def test_discount_line_is_negative_item():
    r = parse_text("Widget 20.00\nDiscount 5.00-\n")
    prices = {i.name: i.price for i in r.items}
    assert prices["Widget"] == 2000
    assert prices["Discount"] == -500
