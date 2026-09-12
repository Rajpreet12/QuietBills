"""Generates docs/architecture.png for the hackathon submission."""

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from matplotlib.path import Path

fig, ax = plt.subplots(figsize=(11, 15))
ax.set_xlim(0, 11)
ax.set_ylim(0, 15)
ax.axis("off")

COLORS = {
    "source": "#e8eef7",
    "agent": "#dbe9ff",
    "tool": "#fff4d6",
    "decision": "#ffe3d6",
    "silent": "#e6f4ea",
    "flag": "#fde2e2",
    "user": "#efe3ff",
    "border": "#333333",
}


def box(cx, cy, w, h, text, color, fontsize=11, weight="normal"):
    b = FancyBboxPatch(
        (cx - w / 2, cy - h / 2),
        w,
        h,
        boxstyle="round,pad=0.08,rounding_size=0.12",
        linewidth=1.4,
        edgecolor=COLORS["border"],
        facecolor=color,
    )
    ax.add_patch(b)
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fontsize, weight=weight, wrap=True)


def diamond(cx, cy, w, h, text, color, fontsize=10.5):
    pts = [(cx, cy + h / 2), (cx + w / 2, cy), (cx, cy - h / 2), (cx - w / 2, cy), (cx, cy + h / 2)]
    d = plt.Polygon(pts, closed=True, linewidth=1.4, edgecolor=COLORS["border"], facecolor=color)
    ax.add_patch(d)
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fontsize, wrap=True)


def arrow(x1, y1, x2, y2, label="", label_dx=0.15, connectionstyle="arc3,rad=0.0"):
    a = FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle="-|>", mutation_scale=16,
        linewidth=1.3, color=COLORS["border"],
        connectionstyle=connectionstyle,
    )
    ax.add_patch(a)
    if label:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        ax.text(mx + label_dx, my, label, fontsize=9, style="italic", color="#333333")


# Title
ax.text(5.5, 14.6, "QuietBills — Architecture", ha="center", fontsize=18, weight="bold")
ax.text(5.5, 14.15, "An agent that stays silent until there's a real decision to make", ha="center", fontsize=10.5, color="#555555")

# 1. Data source
box(5.5, 13.1, 6.2, 0.85, "Subscription Feed\n(bank/email export — demo: subscriptions.json)", COLORS["source"])

# 2. Agent
box(5.5, 11.7, 7.4, 1.0, "QuietBills Agent — Strands Agents SDK\n(model provider swappable: Groq / Anthropic / Bedrock)", COLORS["agent"], weight="bold")
arrow(5.5, 12.67, 5.5, 12.2)

# 3. Memory check
diamond(5.5, 10.15, 4.6, 1.3, "check_previous_decision\n(pending / dismissed / approved?)", COLORS["decision"], fontsize=9.5)
arrow(5.5, 11.2, 5.5, 10.8)

# Silent branch (dismissed & unchanged)
box(1.7, 8.6, 2.7, 0.85, "Stay Silent\n(no output, no log)", COLORS["silent"])
arrow(4.2, 9.9, 2.6, 8.85, "dismissed,\nunchanged", label_dx=-1.3, connectionstyle="arc3,rad=0.2")

# 4. Fact-check tools
box(7.5, 8.6, 3.6, 1.15, "list_subscriptions\nget_subscription_detail\ndays_until", COLORS["tool"], fontsize=9.5)
arrow(6.5, 9.7, 7.2, 9.2, "new / pending /\nworsened", label_dx=0.15, connectionstyle="arc3,rad=-0.15")

# 5. Needs real decision?
diamond(5.5, 6.9, 4.4, 1.3, "Needs a real\ndecision?", COLORS["decision"], fontsize=10.5)
arrow(7.1, 8.15, 5.9, 7.5)

arrow(3.8, 6.9, 2.6, 8.15, "No", label_dx=-0.3, connectionstyle="arc3,rad=0.3")

# 6. Cost tools
box(7.7, 5.5, 3.4, 0.9, "find_cheaper_alternatives", COLORS["tool"], fontsize=9.5)
arrow(6.8, 6.5, 7.4, 5.95, "Yes", label_dx=0.15)

# 7. Draft tools
box(7.7, 4.1, 3.6, 1.05, "draft_cancellation_message\ndraft_negotiation_script", COLORS["tool"], fontsize=9.5)
arrow(7.7, 5.05, 7.7, 4.65)

# 8. flag_for_user
box(5.5, 2.6, 6.4, 1.05, "flag_for_user\n(reason + recommendation + $ savings + draft)", COLORS["flag"], weight="bold")
arrow(7.0, 3.6, 6.1, 3.15)

# 9. User surface
box(5.5, 1.1, 6.6, 1.0, "CLI (scan / decide) & Streamlit Dashboard\nUser: Approve or Dismiss", COLORS["user"])
arrow(5.5, 2.05, 5.5, 1.6)

# Feedback loop: decision state back to check_previous_decision
arrow(2.2, 1.1, 0.6, 1.1, connectionstyle="arc3,rad=0")
ax.text(0.55, 1.1, "Decision\nstate\n(persisted)", ha="right", va="center", fontsize=9, style="italic")
arrow(0.6, 1.5, 0.6, 9.5, connectionstyle="arc3,rad=0")
arrow(0.6, 9.9, 3.2, 10.1, "remembered\nnext scan", label_dx=0.2, connectionstyle="arc3,rad=-0.2")

plt.tight_layout()
plt.savefig("docs/architecture.png", dpi=200, bbox_inches="tight")
print("saved docs/architecture.png")
