# 14 Nov, 16:25 CET — v7 is live and it pulls the attribute lever; conversion not readable yet

`skore_money_v7` (product attributes: the shopper's attribute profiles, attributes shared with the last view,
an attribute prior for new products) replaced v6 at 15:12:16 UTC and runs against `skore_money_v5`.

## The mechanism check passes

What each arm shows, from `ab_mechanism.py` (known shoppers: products not bought; session: requests with a
recent view, the viewed product excluded):

| Share of impressions… | v5 | v6 | v7 |
|---|---|---|---|
| with attribute affinity under 1.0 (the band that sells 0.03–0.05%) | 38.3% | 39.7% | **10.3%** |
| with attribute affinity over 1.25 (sells 0.19–0.30%) | 42.5% | 41.9% | **75.1%** |
| sharing 1 attribute with the last view — known / new shoppers | 20% / 19% | 18% / 20% | **37% / 40%** |
| sharing 2 attributes with the last view — known / new shoppers | 0.7% / 0.6% | 0.6% / 0.5% | **2.4% / 3.4%** |
| in a subcategory the shopper has bought | 62.3% | 61.2% | 57.5% |
| products added during the event | 4.0% | 6.5% | 7.1% |

v7 does what the analysis asked: three quarters of what it shows a known shopper now carries attributes they
buy, and it shows twice as many products that share an attribute with the one just viewed.

## Conversion: ten minutes, not readable

| Arm (period, UTC) | Known shoppers | New shoppers | All |
|---|---|---|---|
| v5 (14:55–15:22) | 1.46% (20 / 1,374) | 2.63% (16 / 608) | 1.82% (36 / 1,982) |
| v7 (15:12–15:22) | 1.44% (12 / 834) | 2.02% (7 / 347) | 1.61% (19 / 1,181) |
| v6 (14:55–15:12, ended) | 0.81% (8 / 992) | 3.07% (12 / 391) | 1.45% (20 / 1,383) |

Two standard errors are ±0.8 points for v7's known shoppers. If the per-impression table held exactly, v7's
known shoppers would be at about 2.1% instead of 1.46% — inside that band, so neither confirmed nor refuted.
It needs until about 17:00 CET. A caution worth keeping in mind: the affinity effect was measured on
impressions v4 and v5 chose for other reasons too, so the products v7 adds at the margin may sell less than
the table says. The A/B is the test; the tick after next should show it.

v6 was behind on known shoppers when it was replaced (0.81% against 1.46%, 1.5 standard errors — not
conclusive, but the right call given v7 was ready).

## Brand history, last word for now

Inside every attribute-affinity band a bought brand still sells 2.2–3× more on the carousel (slot-adjusted:
0.020% → 0.064% in the low band, 0.171% → 0.379% in the top one). So brand is not a stand-in for attributes.
But the model session's ablation found no gain from brand features, and in the organic history brand says
nothing once the subcategory is fixed. The most likely reconciliation is that "bought this brand" tracks how
many times the shopper bought in that subcategory or category, which the model already knows. Not a priority.

## Where we stand against the reference

Leaderboard 16:22 CET: 1.80 (rank 1; team_19 1.63, team_26 1.58), reference 2.11, baseline 0.72 — 78% of the
way. Cold 2.44 against the reference's 1.92. Every request answered since 15:43 CET; `on_time` back to 97%.
The remaining 0.31 points: about 0.1 is the exploration arm, the rest is known shoppers — which is exactly
what v7 is aimed at.

## For the final

The attribute features need only the description of the product and, for the session version, the request
itself; v7's lists for new shoppers moved as much as for known ones. Ranking cost doubled (45 ms per request
against 23) with p95 still at 1.7 s; worth watching under the final's load.
