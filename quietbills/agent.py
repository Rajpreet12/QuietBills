"""Builds the QuietBills Strands agent."""

from __future__ import annotations

import os

from strands import Agent

from .tools import (
    check_previous_decision,
    days_until,
    draft_cancellation_message,
    draft_negotiation_script,
    find_cheaper_alternatives,
    flag_for_user,
    get_subscription_detail,
    list_subscriptions,
)

SYSTEM_PROMPT = """You are QuietBills, an agent that watches a person's \
recurring bills and subscriptions so they don't have to check them \
manually. You run in the background. Your default behavior is SILENCE.

You only call flag_for_user when a subscription needs a real, one-time \
human decision. That means one of:
- The price at the upcoming renewal is meaningfully higher than the \
recent price history (a hike of roughly 10% or more).
- The subscription hasn't been used in 45+ days and is about to renew.
- The renewal is happening very soon (within 3 days) AND is unused or \
just had a price hike, so there's limited time to act.

Do NOT flag a subscription just because it renews soon if it is being \
used normally and its price is stable -- that is exactly the kind of \
routine renewal that should stay quiet.

Before doing anything else, call check_previous_decision. Its status \
field controls what you do next:
- status is missing, or "pending": the user hasn't acted on this yet, so \
flag it again if it still meets the criteria above -- an unresolved \
decision should keep surfacing, that's not nagging.
- status is "dismissed": the user already saw this and chose to leave it \
alone. Stay silent UNLESS the situation has materially worsened (a \
bigger price hike, still unused much later).
- status is "approved": the user already decided to act (e.g. cancel). \
Assume they're handling it -- stay silent unless the subscription is \
still active and renewing again in a later cycle.

When you do flag something:
1. Use get_subscription_detail and days_until to confirm the facts.
2. If cost is the issue, use find_cheaper_alternatives to judge whether \
the price is out of line and to ground your negotiation target in a \
real number.
3. Decide on ONE recommended_action: "cancel", "negotiate", or "downgrade".
4. Estimate potential_monthly_savings: for "cancel" this is the full \
current price; for "negotiate"/"downgrade" it's the gap between the \
current price and the cheaper target you found.
5. Draft the actual text the user would need (draft_cancellation_message \
for a cancellation, draft_negotiation_script for a negotiation call) and \
pass it as draft_text.
6. Call flag_for_user exactly once per subscription that needs a decision.

For every other subscription, do nothing -- do not call flag_for_user, \
do not narrate that you checked it. Silence is the correct output for a \
healthy subscription.
"""


def _build_model():
    provider = os.environ.get("QUIETBILLS_PROVIDER", "bedrock").lower()

    if provider == "anthropic":
        from strands.models.anthropic import AnthropicModel

        model_id = os.environ.get("QUIETBILLS_MODEL_ID", "claude-sonnet-5")
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "QUIETBILLS_PROVIDER=anthropic requires ANTHROPIC_API_KEY to be set."
            )
        return AnthropicModel(
            client_args={"api_key": api_key, "timeout": 60.0},
            model_id=model_id,
            max_tokens=2048,
        )

    if provider == "groq":
        from strands.models.openai import OpenAIModel

        model_id = os.environ.get("QUIETBILLS_MODEL_ID", "openai/gpt-oss-120b")
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("QUIETBILLS_PROVIDER=groq requires GROQ_API_KEY to be set.")
        return OpenAIModel(
            client_args={
                "api_key": api_key,
                "base_url": "https://api.groq.com/openai/v1",
                "timeout": 60.0,
                "max_retries": 0,  # we handle retries ourselves in scan.py
            },
            model_id=model_id,
            stream=False,
            params={"max_tokens": 4096},
        )

    from strands.models import BedrockModel

    model_id = os.environ.get("QUIETBILLS_MODEL_ID", "us.anthropic.claude-sonnet-5")
    region = os.environ.get("AWS_REGION", "us-east-1")
    return BedrockModel(model_id=model_id, region_name=region)


def build_agent(verbose: bool = True) -> Agent:
    model = _build_model()

    kwargs = {} if verbose else {"callback_handler": None}

    return Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[
            list_subscriptions,
            get_subscription_detail,
            days_until,
            find_cheaper_alternatives,
            check_previous_decision,
            draft_cancellation_message,
            draft_negotiation_script,
            flag_for_user,
        ],
        **kwargs,
    )
