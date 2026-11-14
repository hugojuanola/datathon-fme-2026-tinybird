# Best model so far

The version we go back to if a newer one does not hold. Updated at every change, with the evidence.

**How "best" is decided.** Expected purchases per 100 requests on the organisers' own metric
(`python scripts/arms.py HH:MM HH:MM`), against other versions **over the same minutes** and over enough
traffic. Not the peak of a 15-minute window: the level of a window depends on who happens to arrive (the
reference moves with us, from 1.70 to 2.22 this afternoon), and three arms that were doing exactly the same
read 1.92, 2.40 and 2.59 in one quarter of an hour. And it must not lean on ids: the final brings shoppers,
products and trends nobody has seen.

## The best proven version: `v9`

| | |
|---|---|
| What it is | Rules retrieve 1,000 products → two LightGBM models rank them, `P(click) × P(purchase | click)`, 52 features without ids. Its main ingredient is the shopper's taste for the attributes named in the product descriptions |
| Where it is | `models/v9/` (commit `56b4084`); reproducible with `python -m offline.train v9` |
| Evidence | 2.37 expected purchases per 100 requests on 2,822 requests (15:41–16:29 UTC, 14 Nov): cold 2.84, warm 2.11. The reference over the same afternoon: 2.06. Still serving a quarter of the traffic tonight |
| Put it back | In `reco/serve.py`: `ARMS = (("skore_money_v9", "model", "v9", {}, 100),)`, then `powershell -ExecutionPolicy Bypass -File scripts\swap_server.ps1` (no gap, self-test before taking over) |

Nothing is ever lost: every ranker that has served is in `models/` and in git, and every answer is tagged
with its `model_version`.

## What is being measured against it (the night of 14 Nov)

One experiment, eight arms, the same requests ([`docs/findings.md`](docs/findings.md) §17):

| Ranker set-up | Trend lift off | Trend lift on |
|---|---|---|
| `v9` for every request (the best proven) | `skore_money_v21` | `skore_money_v22` |
| `v9w` for cold requests, `v9` for the rest | `skore_money_v23` | `skore_money_v24` |
| `v16` for every request (retrained on all of Saturday) | `skore_money_v25` | `skore_money_v26` |
| `v16w` for cold requests, `v16` for the rest | `skore_money_v27` | `skore_money_v28` |

Read it on Sunday morning with `python scripts/arms.py 17:45 07:30` (UTC). The set-up that wins, with the
lift if it helped while a trend ran, becomes the single arm of the final and the new entry here. If none
beats `v9` clearly, `v9` serves the final.

## How we got here

| Version | What changed | Expected purchases per 100 requests | Reference, same hours |
|---|---|---|---|
| baseline | all-time best sellers in stock | 0.6 | |
| v4 | rules: popularity × measured lifts (session, abandoned carts) | 1.45 | 2.04 |
| v5 | first learned ranker on top of the rules | 1.81 | 2.10 |
| v6 | + new products, price, age of the cart | 1.70 | 2.10 |
| **v7** | **+ the attributes named in the descriptions** | **2.42** | 2.10 |
| v8 | v7 without brand history | 2.35 | 2.10 |
| **v9** | + attribute pair, purchases in the subcategory | **2.37** | 2.06 |
| v9w | v9 with live feedback weighted ×20 | 2.32 (cold 3.21, warm 1.87) | 2.06 |
| v10, v16 | + carts by subcategory, brand; v16 also all of Saturday's feedback, real prices, the trend as a feature | within noise of v9 so far | |
| trend lift | products of a subcategory that is trending get its lift (detector on `shop.events`) | not measured live yet: no trend has run since it was deployed | |

Team level, last hour at 19:00 CET: 2.2 against 1.8 for the next team and 2.0 for the reference; cold
requests 2.8 against 1.7 for the reference. In every 15-minute window since 16:25 CET we have been 4 % to
13 % above the reference, whatever the level of the window.

## Log

- **14 Nov 16:41 CET** — `v9` live (34 % of the traffic, then the control of every later test).
- **14 Nov 17:00 CET** — `v9w`, `v9d` against `v9`: v9w level overall, better on cold; v9d (one model for
  the purchase) worse → dropped.
- **14 Nov 18:15 CET** — trend detector live (`skore_money_v14`, `v15`). No trend since.
- **14 Nov 18:45 CET** — `v16` / `v16w` trained; overnight experiment `skore_money_v21`–`v28` live.
- **14 Nov 18:58 CET** — the server runs as a process of its own (`scripts\swap_server.ps1`): closing a
  terminal or an assistant session no longer stops it.
