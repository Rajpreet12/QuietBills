"""Tools QuietBills' agent can call.

Each tool is a narrow, auditable action. The agent decides *when* to use
them; the tools themselves never decide anything -- they just look things
up or draft text for a human to send.
"""

from __future__ import annotations

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
def flag_for_user(subscription_id: str, reason: str, recommended_action: str, draft_text: str = "") -> str:
    """Surface a subscription to the user because it needs a real decision
    (a price hike, an unused renewal, or a due date with no clear default).
    This is the ONLY tool that produces user-visible output -- everything
    else the agent checks stays silent unless this tool is called.

    Args:
        subscription_id: The id of the subscription being flagged.
        reason: One or two sentences explaining why this needs a decision.
        recommended_action: What the agent recommends (e.g. "cancel", "negotiate", "let it renew").
        draft_text: Optional drafted email/script the user can act on directly.
    """
    entry = {
        "subscription_id": subscription_id,
        "status": "flagged",
        "reason": reason,
        "recommended_action": recommended_action,
        "draft_text": draft_text,
    }
    data_store.append_decision_log(entry)
    return f"Flagged {subscription_id} for user review."
