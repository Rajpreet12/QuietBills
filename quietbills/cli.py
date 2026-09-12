"""Command-line entry point for QuietBills.

    python -m quietbills.cli scan   Run the agent over all tracked subscriptions.
                                     Only prints something for subscriptions
                                     that need a real decision.
    python -m quietbills.cli chat   Ask QuietBills questions in a REPL.
"""

from __future__ import annotations

import json
import logging
import sys

from . import data_store
from .agent import build_agent

logging.getLogger("strands").setLevel(logging.ERROR)


def run_scan() -> None:
    agent = build_agent(verbose=False)
    subs = data_store.load_subscriptions()

    print(f"QuietBills is reviewing {len(subs)} subscriptions...\n")

    for sub in subs:
        prompt = (
            f"Review subscription '{sub.id}' ({sub.name}) and decide whether "
            f"it needs to be flagged for the user. Use your tools to check "
            f"its details, then either call flag_for_user or do nothing."
        )
        agent(prompt)

    log = data_store.read_decision_log()
    flagged_ids = {e["subscription_id"] for e in log}

    if not flagged_ids:
        print("Everything looks normal. No decisions needed today.")
        return

    print(f"{len(flagged_ids)} of {len(subs)} subscriptions need your input:\n")
    print("=" * 60)
    for entry in log:
        if entry["subscription_id"] not in flagged_ids:
            continue
        sub = data_store.get_subscription(entry["subscription_id"])
        name = sub.name if sub else entry["subscription_id"]
        print(f"\n[{name}]")
        print(f"  Why: {entry['reason']}")
        print(f"  Recommended: {entry['recommended_action']}")
        if entry.get("draft_text"):
            print(f"  Draft ready:\n    " + entry["draft_text"].replace("\n", "\n    "))
    print("\n" + "=" * 60)


def run_chat() -> None:
    agent = build_agent()
    print("QuietBills chat. Ask about your subscriptions. Ctrl+C to exit.\n")
    while True:
        try:
            user_input = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user_input:
            continue
        agent(user_input)
        print()


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in ("scan", "chat"):
        print(__doc__)
        sys.exit(1)

    # Reset the decision log for a fresh scan each run.
    if sys.argv[1] == "scan":
        data_store.DECISIONS_FILE.write_text(json.dumps([]))
        run_scan()
    else:
        run_chat()


if __name__ == "__main__":
    main()
