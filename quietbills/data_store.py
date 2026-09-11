"""Loads tracked subscriptions and persists the agent's decision log.

In this demo the subscription feed is a local JSON file, standing in for
a bank/email export. Swapping load_subscriptions() for a real connector
(Plaid, Gmail receipts, etc.) is the only change needed to go from demo
to production feed.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .models import Subscription

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SUBSCRIPTIONS_FILE = DATA_DIR / "subscriptions.json"
DECISIONS_FILE = DATA_DIR / "decisions_log.json"


def load_subscriptions() -> list[Subscription]:
    raw = json.loads(SUBSCRIPTIONS_FILE.read_text())
    return [Subscription.from_dict(item) for item in raw]


def get_subscription(subscription_id: str) -> Subscription | None:
    for sub in load_subscriptions():
        if sub.id == subscription_id:
            return sub
    return None


def append_decision_log(entry: dict) -> None:
    entry = {**entry, "logged_at": datetime.now(timezone.utc).isoformat()}
    log = []
    if DECISIONS_FILE.exists():
        log = json.loads(DECISIONS_FILE.read_text())
    log.append(entry)
    DECISIONS_FILE.write_text(json.dumps(log, indent=2))


def read_decision_log() -> list[dict]:
    if not DECISIONS_FILE.exists():
        return []
    return json.loads(DECISIONS_FILE.read_text())
