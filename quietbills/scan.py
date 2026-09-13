"""Shared scan logic used by both the CLI and the Streamlit dashboard."""

from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from strands.types.exceptions import ModelThrottledException

from . import data_store
from .agent import build_agent

# Free-tier model APIs (e.g. Groq) cap tokens-per-minute, not just
# tokens-per-day, so too much concurrency here trips a 429 mid-scan. Keep
# this modest -- it still parallelizes meaningfully without blowing past
# a typical ~8k TPM free-tier limit.
MAX_CONCURRENT_REVIEWS = 2
MAX_THROTTLE_RETRIES = 3
MAX_TURNS_PER_REVIEW = 12

# Hard ceiling on the whole scan's wall-clock time. Even with per-request
# timeouts and a turns cap, something can still stall in ways we haven't
# anticipated -- this guarantees run_scan() always returns to the caller
# (e.g. the Streamlit UI) within a bounded time instead of hanging.
OVERALL_SCAN_TIMEOUT_SECONDS = 180


def _review(sub) -> None:
    prompt = (
        f"Review subscription '{sub.id}' ({sub.name}) and decide whether "
        f"it needs to be flagged for the user. Use your tools to check "
        f"its details, then either call flag_for_user or do nothing."
    )
    agent = build_agent(verbose=False)

    for attempt in range(1, MAX_THROTTLE_RETRIES + 1):
        try:
            # limits={"turns": ...} caps tool-call loop iterations, so a
            # confused model looping between tools without ever calling
            # flag_for_user (or finishing) can't hang this review forever.
            agent(prompt, limits={"turns": MAX_TURNS_PER_REVIEW})
            return
        except ModelThrottledException:
            if attempt == MAX_THROTTLE_RETRIES:
                raise
            time.sleep(2 * attempt)


def run_scan() -> list[dict]:
    """Reviews every tracked subscription and returns the list of flagged
    decisions (empty if everything is healthy). Resets the per-run flag
    log first; decision *state* (data_store.DECISION_STATE_FILE) persists
    across runs on purpose, so previously dismissed items aren't repeated
    unless something changed.

    Each subscription gets its own fresh agent, reviewed concurrently
    (bounded by MAX_CONCURRENT_REVIEWS) so one review can't bleed context
    into another and the whole scan doesn't wait on each API call in
    sequence. A failure reviewing one subscription (a flaky model
    response, a transient API error) is isolated and doesn't abort the
    rest of the scan.
    """
    data_store.DECISIONS_FILE.write_text(json.dumps([]))

    subs = data_store.load_subscriptions()

    # Not using `with ThreadPoolExecutor(...)` deliberately: its __exit__
    # calls shutdown(wait=True), which would block until every submitted
    # task finishes regardless of any timeout we apply below. Shutting
    # down with wait=False instead lets run_scan() return promptly even
    # if a review is still stuck.
    pool = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_REVIEWS)
    futures = {pool.submit(_review, sub): sub for sub in subs}
    try:
        for future in as_completed(futures, timeout=OVERALL_SCAN_TIMEOUT_SECONDS):
            sub = futures[future]
            try:
                future.result()
            except Exception as exc:
                print(f"  (skipped {sub.id}: {exc})", file=sys.stderr)
    except TimeoutError:
        print(
            f"  (scan exceeded {OVERALL_SCAN_TIMEOUT_SECONDS}s; returning "
            f"whatever was flagged so far)",
            file=sys.stderr,
        )
    finally:
        pool.shutdown(wait=False, cancel_futures=True)

    return data_store.read_decision_log()
