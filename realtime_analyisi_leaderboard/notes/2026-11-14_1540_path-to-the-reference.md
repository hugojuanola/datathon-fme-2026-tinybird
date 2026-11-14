# 14 Nov, 15:40 CET — the path to the reference, point by point

**Where we are.** Leaderboard at 15:37 CET: team_06 1.53 (rank 2 — team_19 passed us with 1.54), reference
2.10, baseline 0.73. The gap is 0.57 points. On the requests it actually serves, `skore_money_v5` converts
**1.94%** (142 purchases in 7,328 requests since 14:34 CET) and earns 1.03 € per request, more than the
reference's 0.94 €. So most of the gap on the board is not the model.

## The budget

| Where the points go | Size today | How it is measured |
|---|---|---|
| Requests we do not answer | **≈ 0.12** | 8.3% unanswered since 15:06 CET (460 of 5,546); a fallback request converts 0.42% (4 / 947) instead of 1.94% |
| The exploration arm | **≈ 0.22** | 20% of the traffic at 0.83% (11 / 1,323) instead of 1.94%. Deliberate, practice only |
| The model itself, against the reference | ≈ 0.16 | 2.10 − 1.94, with v5 known only to about ±0.3 |
| The rest | ≈ 0.07 | the hour on the board still holds 20 minutes of v4, and realised vs expected purchases |

With every request answered and no exploration, today's model would sit at about 1.9 — within reach of the
reference, not yet at it.

About the drop reported at 15:20: it eased. Per six minutes since 15:06 CET: 1.15, 1.13, 1.40, 1.56, 1.93,
1.47. v5 since 15:06 is at 1.60% (65 / 4,063), still 2.2 standard errors under the 2.35% of 14:34–15:06, so
the earlier stretch was probably a lucky one and the truth is near the 1.94% average.

## Where the model still loses: known shoppers, in three places

v5 converts new shoppers at 2.78% (61 / 2,193) — well above the reference's cold 1.96 — and known shoppers at
1.58% (81 / 5,135), against about 2.17 implied for the reference. Inside the known shoppers:

**1 · The `home` page — 20% of their requests, 7% of their purchases.**

| Page | Requests | Purchases | Conversion | Purchases per click |
|---|---|---|---|---|
| category | 1,218 | 24 | 1.97% | 35% |
| product | 2,893 | 51 | 1.76% | 29% |
| **home** | 1,024 | 6 | **0.59%** | 17% |

On `home` there is no session, so everything must come from the shopper's history — and a known shopper has
one. If `home` reached 1.5%, the overall number would rise by about **0.13**.

**2 · Repeat visits — a third of their requests and growing.**

| Request of the shopper since 13:40 CET | Requests | Purchases | Conversion | Purchases per click |
|---|---|---|---|---|
| First | 3,442 | 65 | 1.89% | 33% |
| Later ones | 1,693 | 16 | **0.95%** | 20% |

A returning shopper sees much the same list they already passed over. Recovering half of that difference is
worth about **0.11** overall, and more in the second hour of a round, when most requests are repeat visits.

**3 · Shoppers with a medium history.**

| Purchases in the 60 days | Share of known requests | v5 | v4 (rules) |
|---|---|---|---|
| 0 | 4% | 0.49% | 0.00% |
| 1–4 | 21% | 0.64% | 0.43% |
| 5–9 | 19% | 1.52% | 0.98% |
| 10–19 | 22% | **1.36%** | 1.35% |
| 20+ | 34% | **2.46%** | 1.36% |

The learned ranker's gain is concentrated in the heaviest buyers (2.46% against 1.36%). Shoppers with 10–19
purchases did not move, and the light ones remain low.

## What to do, in order

1. **Answer every request** (+0.12, and the 10 reliability points of the final). A new server instance with
   hedged requests started at 15:35 CET and its first minutes are clean (1 unanswered in 273).
2. **No exploration arm in the final** (+0.22 against today's board). Keep it now: it is what makes the next
   model trainable and testable.
3. **`home` for known shoppers** (≈ +0.13). Check what v5 puts there: with no session, the 500 candidates
   should come from the shopper's purchase subcategories (their top products, not yet bought) and abandoned
   carts, not from global popularity.
4. **Impression discounting for repeat visits** (≈ +0.11): lower the score of a product each time it was shown
   to the same shopper without a click, so the list rotates. It is a standard technique with a simple form —
   a decay in the number of past impressions and the time since the last one [1].
5. **Medium-history shoppers**: the purchase-share features are noisy with few purchases; shrink them towards
   the shopper's category-level shares or towards shoppers of the same device and region.

Items 1 and 2 are operations and add up to more than the model gap. Items 3 and 4 together are worth about
0.24 — enough, on today's numbers, to pass the reference.

## For the final

- Items 3–5 use the shopper's history. For shoppers first seen in the final that history is whatever the live
  stream gave us, so the `home` rule must work from live purchases and carts alone.
- Repeat visits exist for new shoppers too, and their share grows through the two hours: impression
  discounting generalises as it is.
- New shoppers are where we already beat the reference; nothing here should touch that path.

## How it was measured

One light query joining `shop.requests`, `team_06.feedback` and `team_06.submissions` since 13:40 CET, joined
locally to the cached 60-day purchase counts per shopper. Purchases are realised ones; the leaderboard counts
expected purchases, which agree on average.

## Source

1. Lee, Lakshmanan, Tiwari, Shah, *Modeling impression discounting in large-scale recommender systems*, KDD
   2014 — <https://www.aminer.org/pub/5550453645ce0a409eb549ac/modeling-impression-discounting-in-large-scale-recommender-systems>
