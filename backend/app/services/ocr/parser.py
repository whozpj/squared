"""Turn OCR text lines into a structured receipt (DESIGN.md §4 Phase 3).

Token-level normalization only (fix common OCR digit confusions); NO total-driven
guessing — reconciliation (reconcile.py) decides whether the result is trustworthy.
"""

from __future__ import annotations

import re

from app.services.ocr.types import ParsedItem, ParsedReceipt

# Common OCR confusions, applied ONLY to tokens we're trying to read as money.
_CONFUSIONS = str.maketrans({"O": "0", "o": "0", "l": "1", "I": "1", "|": "1", "S": "5", "B": "8"})

# A price at the end of a line: optional $, digits/confusable-digits, dot, 2 decimals,
# optional trailing negative marker.
_PRICE = r"[$]?\s*[\dOolISB,]+[.,][\dOolISB]{2}"
_LINE_PRICE_RE = re.compile(rf"^(?P<name>.*?)[\s.]*(?P<price>{_PRICE})\s*(?P<neg>-|CR)?\s*$")

_NOISE = (
    "THANK", "VISA", "MASTERCARD", "AMEX", "DISCOVER", "CASH", "CHANGE", "TENDER",
    "AUTH", "APPROVAL", "CARD", "ACCOUNT", "ACCT", "TERMINAL", "REF", "SERVER",
    "TABLE", "GUEST", "ORDER", "CHECK #", "PHONE", "TEL", "WWW", "HTTP",
)


def parse_money(token: str) -> int | None:
    """Parse a money token to signed cents, fixing OCR confusions. None if not money."""
    t = token.strip()
    neg = False
    if t.endswith("CR"):
        neg, t = True, t[:-2].strip()
    if t.endswith("-"):
        neg, t = True, t[:-1].strip()
    t = t.replace("$", "").replace(",", "").replace(" ", "")
    if not t:
        return None
    t = t.translate(_CONFUSIONS).replace(",", ".")
    if not re.fullmatch(r"\d+\.\d{2}", t):
        return None
    cents = int(t.replace(".", ""))
    return -cents if neg else cents


def _classify(name_upper: str) -> str:
    if "SUBTOTAL" in name_upper or "SUB TOTAL" in name_upper:
        return "subtotal"
    if "TOTAL" in name_upper or "BALANCE DUE" in name_upper or "AMOUNT DUE" in name_upper:
        return "total"
    if "TAX" in name_upper or "GST" in name_upper or "VAT" in name_upper:
        return "tax"
    if "TIP" in name_upper or "GRATUITY" in name_upper:
        return "tip"
    if any(k in name_upper for k in _NOISE):
        return "noise"
    return "item"


def parse_text(text: str) -> ParsedReceipt:
    receipt = ParsedReceipt(raw_text=text)
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = _LINE_PRICE_RE.match(line)
        if not m:
            continue
        price = parse_money(m.group("price") + (m.group("neg") or ""))
        if price is None:
            continue
        name = m.group("name").strip(" .-\t")
        if not name:
            continue  # a bare price with no label; totals are labeled, so skip
        kind = _classify(name.upper())
        if kind == "subtotal":
            receipt.subtotal = price
        elif kind == "total":
            receipt.total = price
        elif kind == "tax":
            receipt.tax = (receipt.tax or 0) + price  # receipts can list multiple taxes
        elif kind == "tip":
            receipt.tip = price
        elif kind == "item":
            receipt.items.append(ParsedItem(name=name, price=price))
        # noise: dropped
    return receipt
