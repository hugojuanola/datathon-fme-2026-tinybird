# 14 Nov, 14:25 CET — generalisation, the reference, and which techniques fit

Three questions behind every model decision from here on: will it still work in the final (new shoppers,
new products, new trends)? where exactly does the reference beat us? which techniques from the literature are
worth their cost on this data?

## 1 · Generalisation: what survives when the shoppers are new

The final "switches to new data (new shoppers, new products, new trends)". We cannot count on the 60-day
history of a shopper being there. Two measurements on the practice stream say how much that costs.

**How fast the live stream alone builds a history** — requests of the first two hours of the stream (the
final lasts two hours), share whose shopper already had live events *before* the request
([`generalisation_coverage.sql`](../queries/generalisation_coverage.sql)):

| Minutes into the stream | With a live view | With 5+ live views | With a live cart | With a live purchase |
|---|---|---|---|---|
| 0–30 | 24% | 12% | 10% | 6% |
| 30–60 | 50% | 31% | 23% | 15% |
| 60–90 | 65% | 44% | 31% | 21% |
| 90–120 | 74% | 55% | 40% | 28% |

**Does the purchase-history lever work with live-only history?** — carousel feedback per impression, using
only `shop.events` before the request and ignoring the 60 days
([`generalisation_lever_live_only.sql`](../queries/generalisation_lever_live_only.sql)):

| Shopper | Live history in the product's subcategory | Impressions | Purchases | Purchases / impression |
|---|---|---|---|---|
| New | bought | 1,337 | 9 | 0.673% (**5.8×**) |
| New | only viewed | 7,223 | 29 | 0.401% (3.5×) |
| New | none | 87,840 | 102 | 0.116% |
| Known | bought | 6,425 | 15 | 0.233% (**3.5×**) |
| Known | only viewed | 26,949 | 25 | 0.093% (1.4×) |
| Known | none | 190,237 | 126 | 0.066% |

So the lever is not a memory of the 60 days: it works for shoppers we first met during the stream, and by the
second hour a quarter of the requests come from a shopper with a live purchase. Consequences for the model:

- **Every shopper feature must be computable from the live stream**, and the state must start filling from the
  first second of the final. `reco/features.py` does this (running totals per shopper); keep it that way.
- **Train for missing history.** In the log every shopper has 60 days behind them; in the final many have
  minutes. Add training rows where the shopper's history is truncated or empty ("history dropout"), so the
  model learns what to do with little, instead of learning that a thin history means a bad shopper.
- **Validate the way the final will test us**: hold out *shoppers* (not just days), and score the hold-out
  three ways — full history, live-only history, no history. A model that only wins with full history is a
  model for the practice round.
- **No identifiers as features** (already the rule), and shrink per-product rates towards the store average
  for products with few events (already done with a 50-view prior).

## 2 · The reference: where it beats us

Leaderboard at 14:13 CET, and our own feedback of the last 30 minutes:

| | Overall | Cold | Known shoppers (implied / measured) | € per request |
|---|---|---|---|---|
| Reference | 2.03 | 1.90 | ≈ 2.09 (implied, cold ≈ 32% of requests) | 0.94 |
| team_06 (v4) | 1.30 | 1.81 | 1.07 measured (3,756 requests) | 0.55 |
| Baseline | 0.71 | 1.22 | ≈ 0.47 (implied) | 0.11 |

- On cold requests we are at 95% of the reference. On known shoppers we are at about half.
- The baseline converts known shoppers at 0.47 and new ones at 1.22: with best sellers, a known shopper is
  worth less than half a new one, because they already own the best sellers and the carousel will not sell
  them again. The reference converts both about equally, so **it recovers that loss by using the shopper's
  history** — exactly the lever of [the 14:06 note](2026-11-14_1406_known-shoppers-gap.md).
- Revenue per purchase is similar (reference ≈ 46 €, us ≈ 42 €, baseline ≈ 16 €): the reference is not winning
  by pushing price, it is winning purchases.
- If the final has mostly new shoppers, our gap to the reference will be much smaller than it looks today —
  and the cold-start side is where to protect what we have.

## 3 · Which techniques fit, in order of expected return

| # | Technique | Why here (our evidence) | What the literature says | Cost |
|---|---|---|---|---|
| 1 | **Gradient-boosted ranker on shopper × product features**, target = purchase, scored for the whole catalogue | The signals are tabular and strong (subcategory purchase history 6–14×, cart 10×, category affinity 19× CTR); 5,100 products fit in one matrix | Well-tuned simple models match or beat neural recommenders in most reproducibility studies [1][2][3] | In progress (`offline/train.py`) |
| 2 | **Position as a feature in training, fixed at serving** | Slot 1 gets 6.7× the clicks of slot 10, and the log has every product at many slots | The simple alternative to inverse-propensity weighting, which is unbiased in theory [4][5] but high-variance and fragile when propensities are misestimated [6] | Free (`slot` already a feature) |
| 3 | **Train on live feedback, not only on the log** | The log and organic events contain re-purchases; the live carousel does not sell a bought product (3 purchases in 10,618 impressions) | — (this is a property of this simulator) | Weight or flag live rows (`is_live` exists) |
| 4 | **A small, logged randomisation in the live policy** (e.g. swap two adjacent slots or sample among near-ties, recording the probability) | v4 is deterministic, so our own feedback cannot be used for unbiased offline evaluation; and the old log never showed a cross-category product | Off-policy evaluation for slates needs known propensities; self-normalised and doubly-robust estimators keep the variance down [7][8][9] | A small, bounded loss of conversion on the randomised share |
| 5 | **Rank by purchase, not by click, and watch for cannibalisation** | A request has at most one click; v2/v3 showed that a very clickable product that does not convert costs purchases | The single-choice setting is assortment optimisation: an attractive low-converting item takes the click from a better one | An analysis first: does a strong slot-1 item lower the clicks on slots 2–10? |
| 6 | **Session k-NN / item-to-item co-occurrence as extra candidates and features** | Not measured yet beyond subcategory | Session k-NN is consistently among the best session-based methods [1][3] | One co-occurrence table in RawTree |
| 7 | **Prior + Thompson sampling for new products** | 100 new products appeared one hour in; they convert 6.6 purchases per 100 views against 5.2 for the store, so they deserve a good prior, not a penalty | Learn a prior from content features, then explore with Thompson sampling [10][11] | Small: a Beta prior per product from its subcategory and price |
| 8 | Transformer sequence models (SASRec, BERT4Rec) | Sequences are 0–6 views; one day of work; must answer in 3 s on a laptop | They only pull ahead with large models and data [12] | High — **not recommended** |

## 4 · Two facts about the "moving store"

- **Price drops move purchases, modestly.** 620 products dropped ≈18–20% at 10:30 UTC. Hour before vs hour
  after: their purchases went from 691 to 843 (+22%) while all other products went from 10,207 to 9,848
  (−3.5%) — about +26% relative ([`price_drop_effect.sql`](../queries/price_drop_effect.sql)). Most of it is
  more views, not a higher purchase rate per view (3.26 → 3.52 per 100 views). A second batch of 621 changes
  landed at 12:30 UTC. Worth a feature ("price vs its starting price"); not worth reordering the list around.
- **New products are slightly better than average**, not worse: 986 purchases from 14,945 views.

## 5 · What I will check next

1. Whether the single click per request causes cannibalisation (row 5), on the old log.
2. Item-to-item co-occurrence: does "bought together with the last viewed product" add lift inside a subcategory?
3. Once the learned ranker is live: its conversion on new vs known shoppers and the share of impressions in
   purchase-history subcategories, tick by tick (`tick.py` already reports both).

## Sources

1. Ludewig et al., *Empirical analysis of session-based recommendation algorithms* — <https://eldorado.tu-dortmund.de:443/bitstream/2003/40271/1/Ludewig2021_Article_EmpiricalAnalysisOfSession-bas.pdf>
2. Ferrari Dacrema et al., *A troubling analysis of reproducibility and progress in recommender systems research* — <https://re.public.polimi.it/retrieve/e68a57ea-dc32-45c3-a815-ca28d37aa6c6/a-troubling-analysis-of-reproducibility-and-progress-in-recommender-systems-research.pdf>
3. Ludewig et al., *Performance comparison of neural and non-neural approaches to session-based recommendation* — <https://arxiv.org/pdf/1910.12781>
4. Joachims et al., *Unbiased learning-to-rank with biased feedback* — <https://arxiv.org/pdf/1608.04468>
5. Hu et al., *Unbiased LambdaMART* — <https://arxiv.org/pdf/1809.05818>
6. On the fragility of propensity weighting when propensities are misestimated — <https://arxiv.org/pdf/2207.11785v2>
7. Swaminathan et al., *Off-policy evaluation for slate recommendation* — <https://neurips.cc/virtual/2017/poster/9146>
8. Kiyohara et al., *Doubly robust off-policy evaluation for ranking policies under the cascade behavior model* — <https://arxiv.org/pdf/2202.01562>
9. *Double clipping: less-biased variance reduction in off-policy evaluation* — <https://arxiv.org/pdf/2309.01120>
10. *BayesCNS: a unified Bayesian approach to address cold start and non-stationarity in search systems at scale* — <https://arxiv.org/html/2410.02126v1>
11. *Diversify and conquer: bandits and diversity for an enhanced e-commerce homepage experience* — <https://arxiv.org/html/2309.14046v1>
12. *A reproducible analysis of sequential recommender systems* — <https://arxiv.org/html/2408.03873v1>
