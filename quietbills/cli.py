"""Command-line entry point for QuietBills.

    python -m quietbills.cli scan             Run the agent over all tracked
                                               subscriptions. Only prints
                                               something for subscriptions
                                               that need a real decision.
    python -m quietbills.cli decide <id> <approve|dismiss>
                                               Record what you decided about
                                               a flagged subscription, so the
                                               next scan doesn't re-flag it
                                               unless something changes.
    python -m quietbills.cli chat             Ask QuietBills questions in a
                                               REPL.
"""

from __future__ import annotations

import logging
import sys

from . import data_store
from .agent import build_agent
from .scan import run_scan as _run_scan

logging.getLogger("strands").setLevel(logging.ERROR)


def run_scan() -> None:
    subs = data_store.load_subscriptions()
    print(f"QuietBills is reviewing {len(subs)} subscriptions...\n")

    log = _run_scan()
    flagged_ids = {e["subscription_id"] for e in log}

    if not flagged_ids:
        print("Everything looks normal. No decisions needed today.")
        return

    total_savings = sum(e.get("potential_monthly_savings", 0.0) for e in log)

    print(f"{len(flagged_ids)} of {len(subs)} subscriptions need your input:")
    print(f"Potential savings if you act on all of them: ${total_savings:,.2f}/month\n")
    print("=" * 60)
    for entry in log:
        if entry["subscription_id"] not in flagged_ids:
            continue
        sub = data_store.get_subscription(entry["subscription_id"])
        name = sub.name if sub else entry["subscription_id"]
        print(f"\n[{name}]")
        print(f"  Why: {entry['reason']}")
        print(f"  Recommended: {entry['recommended_action']}")
        savings = entry.get("potential_monthly_savings", 0.0)
        if savings:
            print(f"  Potential savings: ${savings:,.2f}/month")
        if entry.get("draft_text"):
            print(f"  Draft ready:\n    " + entry["draft_text"].replace("\n", "\n    "))
        print(f"  -> To act on this: python -m quietbills.cli decide {entry['subscription_id']} approve")
        print(f"     To leave it for now: python -m quietbills.cli decide {entry['subscription_id']} dismiss")
    print("\n" + "=" * 60)


def run_decide(subscription_id: str, decision: str) -> None:
    if decision not in ("approve", "dismiss"):
        print('Decision must be "approve" or "dismiss".')
        sys.exit(1)
    status = "approved" if decision == "approve" else "dismissed"
    data_store.record_user_decision(subscription_id, status)
    print(f"Recorded: {subscription_id} -> {status}")


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
    if len(sys.argv) < 2 or sys.argv[1] not in ("scan", "chat", "decide"):
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    if command == "scan":
        run_scan()
    elif command == "decide":
        if len(sys.argv) != 4:
            print("Usage: python -m quietbills.cli decide <subscription_id> <approve|dismiss>")
            sys.exit(1)
        run_decide(sys.argv[2], sys.argv[3])
    else:
        run_chat()


if __name__ == "__main__":
    main()
