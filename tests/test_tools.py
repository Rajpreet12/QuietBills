"""Unit tests for the QuietBills tool layer, exercised directly (no LLM
call involved) so the data plumbing can be verified independent of model
access.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from quietbills import data_store
from quietbills.tools import (
    check_previous_decision,
    days_until,
    draft_cancellation_message,
    draft_negotiation_script,
    find_cheaper_alternatives,
    flag_for_user,
    get_subscription_detail,
    list_subscriptions,
)


@pytest.fixture(autouse=True)
def isolate_data_files(tmp_path, monkeypatch):
    """Tests must never touch the real data/decisions_log.json or
    data/decision_state.json -- those hold the live app's state. Redirect
    both to a scratch directory for the duration of each test."""
    monkeypatch.setattr(data_store, "DECISIONS_FILE", tmp_path / "decisions_log.json")
    monkeypatch.setattr(data_store, "DECISION_STATE_FILE", tmp_path / "decision_state.json")


def test_list_subscriptions_returns_all_mock_entries():
    subs = list_subscriptions()
    ids = {s["id"] for s in subs}
    assert "netflix" in ids
    assert "fitpulse" in ids
    assert len(subs) == 6


def test_get_subscription_detail_includes_price_history():
    detail = get_subscription_detail(subscription_id="cloudsafe")
    assert detail["current_price"] == 19.99
    assert len(detail["price_history"]) == 3


def test_get_subscription_detail_unknown_id():
    detail = get_subscription_detail(subscription_id="doesnotexist")
    assert "error" in detail


def test_days_until_future_date():
    from datetime import date, timedelta

    target = (date.today() + timedelta(days=5)).isoformat()
    assert days_until(target_date=target) == 5


def test_find_cheaper_alternatives_known_category():
    options = find_cheaper_alternatives(category="streaming")
    assert any(o["name"] == "StreamHub Basic" for o in options)


def test_find_cheaper_alternatives_unknown_category():
    assert find_cheaper_alternatives(category="not-a-category") == []


def test_draft_cancellation_message_contains_name_and_reason():
    msg = draft_cancellation_message(subscription_name="FitPulse Gym App", reason="unused for 97 days")
    assert "FitPulse Gym App" in msg
    assert "unused for 97 days" in msg


def test_draft_negotiation_script_contains_prices():
    script = draft_negotiation_script(subscription_name="Netflix Premium", current_price=24.99, target_price=17.99)
    assert "24.99" in script
    assert "17.99" in script


def test_flag_for_user_writes_to_decision_log():
    result = flag_for_user(
        subscription_id="fitpulse",
        reason="Unused for 97 days and about to renew.",
        recommended_action="cancel",
        potential_monthly_savings=14.99,
        draft_text="Subject: Cancel...",
    )
    assert "fitpulse" in result

    log = data_store.read_decision_log()
    assert len(log) == 1
    assert log[0]["subscription_id"] == "fitpulse"
    assert log[0]["recommended_action"] == "cancel"
    assert log[0]["potential_monthly_savings"] == 14.99


def test_check_previous_decision_unseen_subscription():
    result = check_previous_decision(subscription_id="fitpulse")
    assert result == {"previously_reviewed": False}


def test_flag_for_user_records_decision_state_as_pending():
    flag_for_user(
        subscription_id="fitpulse",
        reason="Unused for 97 days.",
        recommended_action="cancel",
        potential_monthly_savings=14.99,
    )
    result = check_previous_decision(subscription_id="fitpulse")
    assert result["previously_reviewed"] is True
    assert result["status"] == "pending"


def test_record_user_decision_updates_state():
    flag_for_user(
        subscription_id="fitpulse",
        reason="Unused for 97 days.",
        recommended_action="cancel",
    )
    data_store.record_user_decision("fitpulse", "dismissed")

    result = check_previous_decision(subscription_id="fitpulse")
    assert result["status"] == "dismissed"
    assert "decided_at" in result
