"""QuietBills dashboard.

    streamlit run quietbills/webapp.py

Shows every tracked subscription, highlights the ones the agent has
flagged, and lets you approve or dismiss each recommendation -- your
choice is remembered, so a dismissed issue won't be re-flagged next scan
unless something about it changes.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import streamlit as st

# Streamlit runs this file standalone (not as part of the `quietbills`
# package), so relative imports don't work -- put the project root on
# sys.path and import absolutely instead.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from quietbills import data_store
from quietbills.scan import run_scan

logging.getLogger("strands").setLevel(logging.ERROR)

st.set_page_config(page_title="QuietBills", page_icon="🔕", layout="centered")

st.title("🔕 QuietBills")
st.caption("An agent that stays silent until there's a real decision to make.")

if "log" not in st.session_state:
    st.session_state.log = data_store.read_decision_log()

col1, col2 = st.columns([1, 3])
with col1:
    if st.button("Run scan now", type="primary"):
        with st.spinner("Reviewing your subscriptions..."):
            st.session_state.log = run_scan()
        st.rerun()

subs = {s.id: s for s in data_store.load_subscriptions()}
flagged = {e["subscription_id"]: e for e in st.session_state.log}
decision_states = data_store.list_decision_states()

pending_savings = sum(
    e.get("potential_monthly_savings", 0.0)
    for sid, e in flagged.items()
    if decision_states.get(sid, {}).get("status") == "pending"
)

with col2:
    st.metric("Potential monthly savings from open flags", f"${pending_savings:,.2f}")

st.divider()

if not flagged:
    st.success("Everything looks normal. No decisions needed today.")
else:
    st.subheader(f"{len(flagged)} of {len(subs)} subscriptions need your input")

for sub_id, sub in subs.items():
    entry = flagged.get(sub_id)
    state = decision_states.get(sub_id, {})

    if entry is None:
        with st.expander(f"✅ {sub.name} -- ${sub.current_price:.2f}/{sub.billing_cycle}"):
            st.write("No action needed. Used regularly, price stable.")
        continue

    status = state.get("status", "pending")
    icon = {"pending": "🟡", "approved": "✅", "dismissed": "⚪"}.get(status, "🟡")

    with st.expander(
        f"{icon} {sub.name} -- ${sub.current_price:.2f}/{sub.billing_cycle} ({status})",
        expanded=(status == "pending"),
    ):
        st.write(f"**Why:** {entry['reason']}")
        st.write(f"**Recommended:** {entry['recommended_action']}")
        savings = entry.get("potential_monthly_savings", 0.0)
        if savings:
            st.write(f"**Potential savings:** ${savings:,.2f}/month")
        if entry.get("draft_text"):
            st.text_area("Draft ready to use", entry["draft_text"], height=120, key=f"draft_{sub_id}")

        if status == "pending":
            c1, c2 = st.columns(2)
            if c1.button("Approve", key=f"approve_{sub_id}"):
                data_store.record_user_decision(sub_id, "approved")
                st.rerun()
            if c2.button("Dismiss for now", key=f"dismiss_{sub_id}"):
                data_store.record_user_decision(sub_id, "dismissed")
                st.rerun()
        else:
            st.caption(f"You already marked this as **{status}**.")
