#!/usr/bin/env python3
"""One figure with only what moves the score: what we choose, where the purchases are, who buys.

Reads numbers.json (written by eda.py) and writes figures/10_score_levers.png.

    python avanced_data_analysis/levers.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
N = json.loads((HERE / "numbers.json").read_text(encoding="utf-8"))
BLUE, ORANGE, INK, INK2, MUTED, GRID, BG = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#fcfcfb"
plt.rcParams.update({
    "figure.facecolor": BG, "axes.facecolor": BG, "savefig.facecolor": BG, "axes.edgecolor": "#c3c2b7",
    "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": INK2, "text.color": INK, "axes.titlesize": 11,
    "axes.titleweight": "bold", "axes.titlelocation": "left", "axes.labelsize": 9, "xtick.labelsize": 8,
    "ytick.labelsize": 9, "legend.fontsize": 8, "legend.frameon": False, "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
})

# Live check of 14 Nov 2026 13:45 CET on team_06.feedback (known shoppers, best-sellers baseline):
# items the shopper had bought in the history got 12 clicks / 11,338 impressions vs 391 / 167,902 for the rest.
LIVE_ALREADY_BOUGHT = (12 / 11338) / (391 / 167902)

levers = [  # (label, multiplier, what it multiplies)
    ("Category the shopper likes\n(top vs bottom affinity)", N["affinity_ctr_top_vs_bottom"], "clicks"),
    ("Product already in recent_views\n(vs any other)", N["in_recent"]["ctr_in"] / N["in_recent"]["ctr_out"], "clicks"),
    ("Slot 1\n(vs slot 10)", N["slot_ctr_ratio_1_vs_10"], "clicks"),
    ("Same subcategory as the last view\n(vs another subcategory)",
     N["relation_buy_pct"]["same subcategory"] / N["relation_buy_pct"]["same category, other subcat."], "purchases"),
    ("Product the shopper already bought\n(live feedback — avoid)", LIVE_ALREADY_BOUGHT, "clicks"),
]

fig, ax = plt.subplots(1, 3, figsize=(17, 5.2), gridspec_kw={"width_ratios": [1.35, 1, 1]})

a = ax[0]
y = np.arange(len(levers))[::-1]
vals = [v for _, v, _ in levers]
a.barh(y, [v - 1 for v in vals], left=1, color=[BLUE if v > 1 else ORANGE for v in vals], height=0.62)
a.axvline(1, color=INK, lw=1)
a.set_xscale("log")
a.set_xlim(0.3, 40)
a.set_xticks([0.5, 1, 2, 5, 10, 20], ["×0.5", "×1", "×2", "×5", "×10", "×20"])
a.set_yticks(y, [lab for lab, _, _ in levers])
for yi, (_, v, what) in zip(y, levers):
    a.text(max(v, 1) * 1.08, yi, f"×{v:.1f} {what}", va="center", ha="left", fontsize=9)
a.set(title="What we choose: which products, in which order", xlabel="effect on the same impression (log scale)")
a.grid(axis="y", visible=False)

a = ax[1]
pages = ["product", "category", "home"]
x = np.arange(3)
req = [100 * N["page"][p]["share_requests"] for p in pages]
buy = [100 * N["page"][p]["share_purchases"] for p in pages]
a.bar(x - 0.2, req, 0.38, color=MUTED, label="% of requests")
a.bar(x + 0.2, buy, 0.38, color=BLUE, label="% of purchases")
for xi, r, b in zip(x, req, buy):
    a.text(xi - 0.2, r + 1, f"{r:.0f}%", ha="center", fontsize=8)
    a.text(xi + 0.2, b + 1, f"{b:.0f}%", ha="center", fontsize=8)
a.set_xticks(x, pages)
a.set(title="Where the purchases are: by page", ylabel="%")
a.legend()
a.grid(axis="x", visible=False)

a = ax[2]
bp = N["buyer_persistence"]
ks = list(bp)
v = [bp[k]["conversion_pct"] for k in ks]
a.bar(ks, v, color=BLUE, width=0.7)
for xi, vi in enumerate(v):
    a.text(xi, vi + 0.06, f"{vi:.2f}", ha="center", fontsize=8)
a.set(title="Who buys: conversion by past purchases", xlabel="purchases in the previous 30 days",
      ylabel="purchases per 100 requests (non-home pages)")
a.grid(axis="x", visible=False)

fig.suptitle("10 · Score levers: only what moves expected purchases per request", x=0.01, ha="left", fontsize=13, fontweight="bold")
fig.tight_layout(rect=(0, 0, 1, 0.94))
fig.savefig(HERE / "figures" / "10_score_levers.png", dpi=130)
print("wrote 10_score_levers")
