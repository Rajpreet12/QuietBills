"""Generates docs/cover.png -- a blog/social cover image for QuietBills."""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, Polygon, Rectangle
from matplotlib.path import Path
from matplotlib.patches import PathPatch

W, H = 16, 8.4  # ~1600x840 at 100dpi, close to a 1200x630 social-card ratio

fig = plt.figure(figsize=(W, H), dpi=100)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.axis("off")

# --- Gradient background (indigo -> violet) ---
top = np.array([0.10, 0.11, 0.30])
bottom = np.array([0.36, 0.20, 0.55])
grad = np.linspace(0, 1, 256).reshape(-1, 1)
grad_rgb = (top[None, :] * (1 - grad) + bottom[None, :] * grad)
gradient_img = np.tile(grad_rgb.reshape(-1, 1, 3), (1, 2, 1))
ax.imshow(gradient_img, extent=[0, W, 0, H], aspect="auto", zorder=0)

rng = np.random.default_rng(7)

# --- Faint decorative "receipt" cards scattered in the background ---
for _ in range(14):
    x = rng.uniform(0.5, W - 0.5)
    y = rng.uniform(0.5, H - 0.5)
    w = rng.uniform(0.7, 1.3)
    h = w * rng.uniform(1.2, 1.6)
    angle = rng.uniform(-18, 18)
    card = Rectangle((x - w / 2, y - h / 2), w, h, angle=angle, rotation_point="center",
                      facecolor="white", alpha=0.05, edgecolor="white", linewidth=0.8, zorder=1)
    ax.add_patch(card)

# --- Central silent bell icon ---
bx, by = W / 2, H * 0.66
bell_color = "#ffe08a"

# Bell body via bezier-ish polygon approximation (simple dome + base)
theta = np.linspace(np.pi, 2 * np.pi, 60)
dome_x = bx + 1.05 * np.cos(theta)
dome_y = by + 0.2 + 1.05 * np.sin(theta)
base_left_x, base_right_x = bx - 1.35, bx + 1.35
base_y = by + 0.2

bell_x = np.concatenate([[base_left_x], dome_x, [base_right_x]])
bell_y = np.concatenate([[base_y], dome_y, [base_y]])
bell_poly = Polygon(np.column_stack([bell_x, bell_y]), closed=True, facecolor=bell_color,
                     edgecolor="#8a5a00", linewidth=2, zorder=3)
ax.add_patch(bell_poly)

# Bell base bar
ax.add_patch(Rectangle((bx - 1.55, base_y - 0.16), 3.1, 0.16, facecolor=bell_color,
                        edgecolor="#8a5a00", linewidth=2, zorder=3))
# Bell clapper knob
ax.add_patch(Circle((bx, base_y - 0.45), 0.22, facecolor=bell_color, edgecolor="#8a5a00", linewidth=2, zorder=3))
# Bell top knob
ax.add_patch(Circle((bx, by + 1.25), 0.13, facecolor=bell_color, edgecolor="#8a5a00", linewidth=2, zorder=3))

# Slash through the bell (the "silent" mark)
slash = FancyArrowPatch((bx - 1.5, by - 1.05), (bx + 1.5, by + 1.55),
                         arrowstyle="-", linewidth=10, color="#ff5c5c", zorder=4,
                         capstyle="round")
ax.add_patch(slash)
slash_outline = FancyArrowPatch((bx - 1.5, by - 1.05), (bx + 1.5, by + 1.55),
                                 arrowstyle="-", linewidth=14, color="white", zorder=3.5,
                                 capstyle="round")
ax.add_patch(slash_outline)

# --- Title ---
ax.text(W / 2, H * 0.30, "QuietBills", ha="center", va="center",
        fontsize=64, weight="bold", color="white", zorder=5,
        family="sans-serif")

# --- Tagline ---
ax.text(W / 2, H * 0.185, "An agent that stays silent until there's a real decision to make",
        ha="center", va="center", fontsize=19, color="#e8e2ff", zorder=5, style="italic")

# --- Small badge ---
ax.text(W / 2, H * 0.07, "AGENTS FOR HUMANS HACKATHON  •  BUILT WITH STRANDS AGENTS SDK",
        ha="center", va="center", fontsize=12.5, color="#c9bfff", zorder=5,
        weight="bold", family="monospace")

plt.savefig("docs/cover.png", dpi=100, bbox_inches="tight", pad_inches=0)
print("saved docs/cover.png")
