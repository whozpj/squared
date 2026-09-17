"""Shared OCR data types (all money in integer cents)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Word:
    """A single OCR'd word with its bounding box and confidence (0-100)."""

    text: str
    x: int
    y: int
    w: int
    h: int
    conf: float


@dataclass
class ParsedItem:
    name: str
    price: int  # signed cents (discount = negative)


@dataclass
class ParsedReceipt:
    items: list[ParsedItem] = field(default_factory=list)
    subtotal: int | None = None
    tax: int | None = None
    tip: int | None = None
    total: int | None = None
    confidence: float = 0.0  # 0..1
    reconciled: bool = False
    issues: list[str] = field(default_factory=list)
    raw_text: str = ""

    def to_dict(self) -> dict:
        return {
            "items": [{"name": i.name, "price": i.price} for i in self.items],
            "subtotal": self.subtotal,
            "tax": self.tax,
            "tip": self.tip,
            "total": self.total,
            "confidence": round(self.confidence, 3),
            "reconciled": self.reconciled,
            "issues": self.issues,
        }
