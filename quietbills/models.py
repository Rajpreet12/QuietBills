"""Data model for a tracked recurring subscription/bill."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PricePoint:
    date: str
    amount: float


@dataclass
class Subscription:
    id: str
    name: str
    category: str
    current_price: float
    billing_cycle: str  # "monthly" | "annual"
    next_renewal_date: str
    auto_renew: bool
    last_used_days_ago: int
    price_history: list[PricePoint] = field(default_factory=list)
    notes: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "Subscription":
        history = [PricePoint(**p) for p in d.get("price_history", [])]
        return cls(
            id=d["id"],
            name=d["name"],
            category=d["category"],
            current_price=d["current_price"],
            billing_cycle=d["billing_cycle"],
            next_renewal_date=d["next_renewal_date"],
            auto_renew=d["auto_renew"],
            last_used_days_ago=d["last_used_days_ago"],
            price_history=history,
            notes=d.get("notes", ""),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "current_price": self.current_price,
            "billing_cycle": self.billing_cycle,
            "next_renewal_date": self.next_renewal_date,
            "auto_renew": self.auto_renew,
            "last_used_days_ago": self.last_used_days_ago,
            "price_history": [p.__dict__ for p in self.price_history],
            "notes": self.notes,
        }
