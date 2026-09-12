"""Shared scan logic used by both the CLI and the Streamlit dashboard."""

from __future__ import annotations

import json
import sys

from . import data_store
from .agent import build_agent


def run_scan() -> list[dict]:
    """Reviews every tracked subscription and returns the list of flagged
    decisions (empty if everything is healthy). Resets the per-run flag
    log first; decision *state* (data_store.DECISION_STATE_FILE) persists
    across runs on purpose, so previously dismissed items aren't repeated
    unless something changed.

    Each subscription gets its own fresh agent so one review can't bleed
    context (or token budget) into the next, and a failure reviewing one
    subscription (a flaky model response, a transient API error) doesn't
    abort the rest of the scan.
    """
    data_store.DECISIONS_FILE.write_text(json.dumps([]))

    subs = data_store.load_subscriptions()

    for sub in subs:
        prompt = (
            f"Review subscription '{sub.id}' ({sub.name}) and decide whether "
            f"it needs to be flagged for the user. Use your tools to check "
            f"its details, then either call flag_for_user or do nothing."
        )
        try:
            agent = build_agent(verbose=False)
            agent(prompt)
        except Exception as exc:
            print(f"  (skipped {sub.id}: {exc})", file=sys.stderr)

    return data_store.read_decision_log()
