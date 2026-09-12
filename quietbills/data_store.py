"""Loads tracked subscriptions and persists the agent's decision log
and decision *state* (memory across runs).

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
DECISION_STATE_FILE = DATA_DIR / "decision_state.json"


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


def _read_decision_state() -> dict:
    if not DECISION_STATE_FILE.exists():
        return {}
    return json.loads(DECISION_STATE_FILE.read_text())


def _write_decision_state(state: dict) -> None:
    DECISION_STATE_FILE.write_text(json.dumps(state, indent=2))


def get_decision_state(subscription_id: str) -> dict | None:
    """Memory of what happened last time this subscription was reviewed:
    whether it was flagged, what the user decided (approve/dismiss), and
    when -- so the agent doesn't nag about the same unresolved issue."""
    return _read_decision_state().get(subscription_id)


def record_flag(subscription_id: str, reason: str, recommended_action: str, potential_monthly_savings: float) -> None:
    state = _read_decision_state()
    state[subscription_id] = {
        "status": "pending",
        "reason": reason,
        "recommended_action": recommended_action,
        "potential_monthly_savings": potential_monthly_savings,
        "flagged_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_decision_state(state)


def record_user_decision(subscription_id: str, decision: str) -> None:
    """decision is 'approved' (user will act on the recommendation) or
    'dismissed' (user has seen it and chose to leave it as-is for now)."""
    state = _read_decision_state()
    entry = state.get(subscription_id, {})
    entry["status"] = decision
    entry["decided_at"] = datetime.now(timezone.utc).isoformat()
    state[subscription_id] = entry
    _write_decision_state(state)


def list_decision_states() -> dict:
    return _read_decision_state()
