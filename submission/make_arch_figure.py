"""Draws the system-architecture diagram (Fig. 1 of the paper) with matplotlib.
Output: submission/figures/fig_architecture.png      Run: python submission/make_arch_figure.py
Box labels with sizes are read from results/metrics.json.
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parent.parent
M = json.loads((ROOT / "results/metrics.json").read_text())
G, CS = M["graph"], M["clickstream"]
ROWS = sum(v["rows_scanned"] for v in CS.values())

BLUE, AMBER, GREEN, GREY = "#2F5FB3", "#C77C0E", "#1F8A5B", "#555555"
plt.rcParams.update({"font.family": "Times New Roman", "font.size": 10})

fig, ax = plt.subplots(figsize=(7.0, 3.9), dpi=300)
ax.set_xlim(0, 7.0)
ax.set_ylim(0, 3.95)
ax.axis("off")

W, H = 1.9, 0.95


def box(x, y, title, sub, color, w=W, h=H):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                linewidth=1.4, edgecolor=color, facecolor="white"))
    ax.text(x + w / 2, y + h * 0.68, title, ha="center", va="center", fontsize=11.5,
            fontweight="bold", color=color)
    ax.text(x + w / 2, y + h * 0.3, sub, ha="center", va="center", fontsize=9, color="#222222",
            linespacing=1.15)


def arrow(p, q, color=GREY, style="-|>", conn="arc3"):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle=style, mutation_scale=13, linewidth=1.3,
                                 color=color, connectionstyle=conn, shrinkA=2, shrinkB=2))


xs = [0.15, 2.55, 4.95]
y1, y2 = 2.0, 0.35
# row 1
box(xs[0], y1, "Wikipedia API", "2-hop crawl from seed\ncached responses", BLUE)
box(xs[1], y1, "Link subgraph", f"{G['nodes']:,} articles\n{G['edges']:,} links", BLUE)
box(xs[2], y1, "Clickstream\nMapReduce", "", AMBER)
ax.texts[-1].set_position((xs[2] + W / 2, y1 + H * 0.62))
ax.text(xs[2] + W / 2, y1 + 0.16, "map · combine · reduce", ha="center", va="center", fontsize=9)
# row 2
box(xs[0], y2, "PageRank\nMapReduce", "", BLUE)
ax.texts[-1].set_position((xs[0] + W / 2, y2 + H * 0.62))
ax.text(xs[0] + W / 2, y2 + 0.16, "standard + click-weighted", ha="center", va="center", fontsize=9)
box(xs[1], y2, "Evaluation", "Spearman ρ, top-10,\nNDCG@10 on July", GREEN)
box(xs[2], y2, "Streamlit", "6-tab dashboard\nreads results/ only", AMBER)
# input: clickstream dumps
ax.add_patch(FancyBboxPatch((xs[2] + 0.02, 3.25), W - 0.04, 0.6, boxstyle="round,pad=0.02,rounding_size=0.06",
                            linewidth=1.0, edgecolor=AMBER, facecolor="#FFF6E8", linestyle="--"))
ax.text(xs[2] + W / 2, 3.55, f"Clickstream dumps\n{ROWS / 1e6:.1f} M rows (Jun + Jul)", ha="center",
        va="center", fontsize=9, linespacing=1.15)
arrow((xs[2] + W / 2, 3.25), (xs[2] + W / 2, y1 + H + 0.03), AMBER)

arrow((xs[0] + W + 0.02, y1 + H / 2), (xs[1] - 0.02, y1 + H / 2))
arrow((xs[1] + W + 0.02, y1 + H / 2), (xs[2] - 0.02, y1 + H / 2))
# wrap from end of row 1 to start of row 2
ymid = (y1 + y2 + H) / 2
ax.plot([xs[2] + W / 2, xs[2] + W / 2, xs[0] + W / 2], [y1 - 0.03, ymid, ymid], color=GREY, lw=1.3)
arrow((xs[0] + W / 2, ymid), (xs[0] + W / 2, y2 + H + 0.03))
ax.text(3.5, ymid + 0.06, "per-link click counts (June) → edge weights",
        ha="center", va="bottom", fontsize=8.5, style="italic", color=GREY)
arrow((xs[0] + W + 0.02, y2 + H / 2), (xs[1] - 0.02, y2 + H / 2))
arrow((xs[1] + W + 0.02, y2 + H / 2), (xs[2] - 0.02, y2 + H / 2))

out = ROOT / "submission/figures/fig_architecture.png"
fig.savefig(out, bbox_inches="tight", pad_inches=0.03, facecolor="white")
print("saved", out)
