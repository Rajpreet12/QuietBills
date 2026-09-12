"""Tools QuietBills' agent can call.

Each tool is a narrow, auditable action. The agent decides *when* to use
them; the tools themselves never decide anything -- they just look things
up or draft text for a human to send.
"""

from __future__ import annotations

import json
from datetime import date

from strands import tool

from . import data_store

# Mock competitor pricing, standing in for a price-comparison web search.
_ALTERNATIVES = {
    "streaming": [("StreamHub Basic", 12.99), ("StreamHub Standard", 17.99)],
    "storage": [("VaultDrive 2TB", 9.99), ("SkyStore 2TB", 11.99)],
    "fitness": [("HomeFit App", 6.99)],
    "food": [("PantryBox Skip-a-week plan", 0.0)],
    "news": [("NewsPlus Digital", 8.0)],
    "software": [("CloudIDE Pro", 12.0)],
}


@tool
def list_subscriptions() -> list[dict]:
    """Return every tracked recurring subscription with its current price,
    renewal date, and how many days since it was last used."""
    return [s.to_dict() for s in data_store.load_subscriptions()]


@tool
def get_subscription_detail(subscription_id: str) -> dict:
    """Return full detail for one subscription, including its full price
    history, so the agent can judge whether a renewal price is a hike.

    Args:
        subscription_id: The id of the subscription, e.g. "netflix".
    """
    sub = data_store.get_subscription(subscription_id)
    if sub is None:
        return {"error": f"no subscription with id '{subscription_id}'"}
    return sub.to_dict()


@tool
def days_until(target_date: str) -> int:
    """Return the number of days between today and target_date (YYYY-MM-DD).
    Negative means the date is in the past.

    Args:
        target_date: An ISO date string, e.g. "2026-09-14".
    """
    today = date.today()
    target = date.fromisoformat(target_date)
    return (target - today).days


@tool
def find_cheaper_alternatives(category: str) -> list[dict]:
    """Look up cheaper alternatives available for a subscription category
    (e.g. "streaming", "storage", "fitness", "food"). Stands in for a live
    price-comparison search.

    Args:
        category: The subscription's category.
    """
    options = _ALTERNATIVES.get(category, [])
    return [{"name": name, "price": price} for name, price in options]


@tool
def draft_cancellation_message(subscription_name: str, reason: str) -> str:
    """Draft a short, polite cancellation email/chat message for a
    subscription, ready for the user to review and send themselves.

    Args:
        subscription_name: The subscription's display name.
        reason: The plain-language reason for cancelling.
    """
    return (
        f"Subject: Cancel my {subscription_name} subscription\n\n"
        f"Hi,\n\nPlease cancel my {subscription_name} subscription effective "
        f"at the end of the current billing period. Reason: {reason}.\n\n"
        f"Please confirm the cancellation and the date my access ends.\n\n"
        f"Thanks."
    )


@tool
def draft_negotiation_script(subscription_name: str, current_price: float, target_price: float) -> str:
    """Draft a short retention-call script the user can read when calling
    to ask for a lower price instead of cancelling outright.

    Args:
        subscription_name: The subscription's display name.
        current_price: What the user is currently being charged.
        target_price: The price the user wants to negotiate down to.
    """
    return (
        f"\"Hi, I'm calling about my {subscription_name} plan. I've been a "
        f"customer for a while, but at ${current_price:.2f} it's more than "
        f"I can justify. Is there a retention offer or discounted plan "
        f"closer to ${target_price:.2f}? If not, I'll need to cancel "
        f"today.\""
    )


@tool
def check_previous_decision(subscription_id: str) -> dict:
    """Check whether this subscription was already reviewed and what the
    user decided last time (approved the recommendation, or dismissed it
    for now). Use this BEFORE flag_for_user so you don't re-flag something
    the user already dismissed unless the situation has materially
    changed (e.g. an even bigger price hike, or it's still unused much
    later).

    Args:
        subscription_id: The id of the subscription to check.
    """
    state = data_store.get_decision_state(subscription_id)
    if state is None:
        return {"previously_reviewed": False}
    return {"previously_reviewed": True, **state}


@tool
def estimate_market_price(category: str, subscription_name: str, current_price: float) -> dict:
    """Reason about whether current_price is above typical market rate for
    this category, using general knowledge of common competitors and
    pricing. This is a best-effort estimate from the model's own
    knowledge, not a live price-comparison search.

    Args:
        category: The subscription's category (e.g. "streaming", "storage").
        subscription_name: The subscription's display name.
        current_price: What the user currently pays per month.
    """
    try:
        from .agent import _build_model
        from strands import Agent as _Agent

        judge = _Agent(
            model=_build_model(),
            system_prompt=(
                "You estimate typical market pricing for subscription "
                "categories from general knowledge. Reply with ONLY a "
                'compact JSON object: {"typical_low_price": <number>, '
                '"typical_high_price": <number>, "note": "<one short '
                'sentence>"}. No other text.'
            ),
            callback_handler=None,
        )
        result = judge(
            f"Category: {category}. Service: {subscription_name}. "
            f"Current price: ${current_price:.2f}/month. What's the "
            f"typical price range for comparable services?"
        )
        text = str(result)
        start, end = text.find("{"), text.rfind("}")
        return json.loads(text[start : end + 1])
    except Exception:
        return {
            "typical_low_price": round(current_price * 0.7, 2),
            "typical_high_price": round(current_price * 0.95, 2),
            "note": "Estimate unavailable; using a generic 5-30% band below current price.",
        }


@tool
def flag_for_user(
    subscription_id: str,
    reason: str,
    recommended_action: str,
    potential_monthly_savings: float = 0.0,
    draft_text: str = "",
) -> str:
    """Surface a subscription to the user because it needs a real decision
    (a price hike, an unused renewal, or a due date with no clear default).
    This is the ONLY tool that produces user-visible output -- everything
    else the agent checks stays silent unless this tool is called.

    Args:
        subscription_id: The id of the subscription being flagged.
        reason: One or two sentences explaining why this needs a decision.
        recommended_action: What the agent recommends (e.g. "cancel", "negotiate", "let it renew").
        potential_monthly_savings: Your best estimate of $/month saved if the user acts on this
            (full price for a cancel, the price difference for a negotiate/downgrade).
        draft_text: Optional drafted email/script the user can act on directly.
    """
    entry = {
        "subscription_id": subscription_id,
        "status": "flagged",
        "reason": reason,
        "recommended_action": recommended_action,
        "potential_monthly_savings": potential_monthly_savings,
        "draft_text": draft_text,
    }
    data_store.append_decision_log(entry)
    data_store.record_flag(subscription_id, reason, recommended_action, potential_monthly_savings)
    return f"Flagged {subscription_id} for user review."
