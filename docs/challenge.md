# The challenge — rules, scoring, timeline

Distilled from the official brief. The verbatim sources are in [`sources/`](sources/README.md); when this
file and a source disagree, the official README ([`sources/challenge-readme.md`](sources/challenge-readme.md)) wins.

## One-paragraph version

An online store (~5,000 products, 10 categories) shows a carousel of 10 recommended products. A shopper
arrives about 3 times per second. For each arrival a record lands in `shop.requests`; we have **3 seconds
from the request `ts`** to insert an ordered list of **10 distinct, active product IDs** into
`team_06.submissions`. A hidden simulator decides whether the shopper clicks and buys, and writes the
outcome to `team_06.feedback`. **Our running system is the submission**: there is no file to upload.

## The loop

```
shop.requests ──▶ our system ──▶ team_06.submissions ──▶ hidden simulator ──▶ team_06.feedback
      ▲                ▲                                                            │
shop.events, shop.catalog_updates (live)  +  shop.history_* (60 days)  ◀────────────┘ learn
```

1. Poll `shop.requests` for new records.
2. Rank the catalogue for that shopper (device, region, page, `recent_views`, user history).
3. Batch-insert answers into `team_06.submissions` (e.g. every 0.3–0.5 s, not one HTTP call per request).
4. Read `team_06.feedback` and the live `shop.events` / `shop.catalog_updates`, improve, redeploy.

Every team gets the same shoppers at the same time.

## Submission rules

Insert one record per request into `team_06.submissions`:

```json
{"request_id": "r_01JD8K3...", "items": ["p_91aa", "...10 ids..."], "model_version": "v3-mf-bandit"}
```

- **Exactly 10 distinct, active product IDs.** Out-of-stock / inactive product → the whole answer is
  `invalid` and replaced by the fallback.
- Must reach RawTree **within 3 s of the request `ts`**, by the organisers' clock (they poll every 0.5 s).
  Late → fallback.
- **One answer per request.** If several are sent only one counts.
- **Order matters**: the first slots get far more attention than the last ones.
- `model_version` is a free string; it is displayed on the public leaderboard next to the team.
- Fallback = the all-time best sellers that are in stock (the starter baseline). `feedback.served_by`
  says `team` or `fallback`; `fallback_reason` is `missing`, `late` or `invalid`.

## Timeline (Barcelona time, CET = UTC+1; data timestamps are UTC)

| When (CET) | UTC | What |
|---|---|---|
| Sat 14 Nov 10:00 → Sun 15 Nov 10:00 | Sat 09:00 → Sun 09:00 | **Practice round.** Live stream, public leaderboard refreshed every 10 min, ranking on the last hour. Does not count. |
| **Sun 15 Nov 10:00 → 12:00** | Sun 09:00 → 11:00 | **Final round — the only thing that is scored.** New shoppers, new products, new trends. Leaderboard hidden; only a green/red status light per team. |
| Sun 15 Nov 12:00 | Sun 11:00 | Stream stops, final ranking appears automatically. |
| Sun 15 Nov 14:00 | | Demos / presentations to the jury. |

- **The best version must be running by Sunday 10:00 CET**, unattended, on a machine that does not sleep.
- Code may keep changing during the final (the system keeps answering), but the ranking is invisible until 12:00.
- Status light: green if >90% of answers in the last 5 minutes were valid and on time. It scores nothing.
- Shoppers keep arriving overnight; unanswered requests get the fallback.

## Scoring

### 70 points — final round, automatic

| Component | Points | Metric |
|---|---|---|
| Conversion | 50 | Expected purchases per 100 requests |
| Cold start | 10 | Same, on **cold requests** only: `is_new_user = true`, or `recent_views` contains a product added during the event (`change = 'new_product'` in `shop.catalog_updates`) |
| Reliability | 10 | Share of requests answered validly and on time |

```
score = 100 × (team − baseline) / (oracle − baseline), clipped to [0, 100]
```

- **baseline (0)**: all-time best sellers in stock, ranked once at the start of the stream. Also the fallback.
- **oracle (100)**: the 10 products the hidden model itself would pick per shopper. Not published.
- **reference**: a strong recommender built by the organisers, shown on the leaderboard. It can be beaten.
- The leaderboard normalises the 70 points to 100 (≈71 conversion, 14 cold start, 14 reliability).
  Final grade = 70% of that score + up to 30 jury points.
- **No luck**: the score uses each shopper's *probability* of buying given the 10 products shown, from the
  hidden model, not the realised coin flip. Feedback shows realised clicks/purchases; they agree on average.
- **Satiation**: a shopper who already bought a product tends not to want it again, so what we sell changes
  later scores.
- **Tie-breaker**: expected revenue per request in the final round.

### Where the oracle is (measured 14 Nov, 20:30 CET)

The leaderboard hides the score during practice (`"hidden": true`), but `/api/state` carries a `progress`
series: one number per team per hour (the hour starting at that timestamp). Across the 42 teams it is exactly
`slope × (conversion − baseline)` for the same hour (error under 0.01; cold start and `on_time` add nothing):
it is the **conversion score**, and `100 / slope` is `oracle − baseline`.

| Hour (UTC) | Oracle | Baseline | Reference (score) | Us: conversion → score | `on_time` | Best rival (score) |
|---|---|---|---|---|---|---|
| 15:00 | 3.49 | 0.67 | 2.10 (50.5) | 2.13 → 51.6 | 100.0 | team_26 (40.8) |
| 16:00 | 3.33 | 0.54 | 1.99 (51.8) | 2.16 → 57.9 | 95.6 | team_26 (45.7) |
| 17:00 | 3.32 | 0.59 | 2.03 (52.9) | 2.21 → 59.4 | 99.9 | team_42 (49.8) |
| 18:00 | 3.10 | 0.45 | 1.84 (52.6) | 1.95 → 56.8 | 93.3 | team_42 (48.9) |

- The oracle sells 3.1–3.5 per 100 requests; the organisers' reference is at 50–53 % of the way, we are at 57–60 %.
- A lost answer scores as the baseline, so it costs conversion as well as reliability: the hour with 93.3 %
  on time scored 2.6 points less than the clean hour before it.
- The cold-start oracle is not derivable from the API (no series for it).

### 30 points — jury (Sunday afternoon, short presentation + demo)

| Criterion | Points | What they look at |
|---|---|---|
| Method | 10 | Sound and well-justified approach; **validated offline before going live** |
| Learning from the stream | 10 | Use of feedback and live events: exploration, trends, price changes, cold start |
| Use of RawTree | 5 | Features computed in SQL, embeddings, how the pipeline reads and writes |
| Communication | 5 | Could a product manager understand what the system does and why it works? |

The top teams share their repository with the jury: **keep the repo readable**.
Anything the team cannot explain in the presentation may be penalised.

## What changes in the final round ("the store moves")

Teams that generalise beat teams that memorise:

- **New shoppers** — many arrive with no history at all.
- **New products** — only a `description`, no interactions yet.
- **Trends** — visible early in the live `shop.events`.
- **Price changes** — announced in `shop.catalog_updates`.
- **Stock-outs** — inactive products make the answer invalid.

**The final continues Saturday's state** (organisers' message, Sun 15 Nov about 09:10 CET, verbatim in
[`sources/final-announcement.md`](sources/final-announcement.md)): "it's the same world, still running.
Nothing resets at 10:00."

- **Purchases still count.** A returning shopper carries everything they bought: in the history, in the
  store on Saturday (`shop.events`) and through our recommendations (`feedback`), and tends not to want it
  again. Our state holds the three (`reco/state.py`: the history cache, the journal of live events, our
  feedback, at start-up and every two seconds) and a product the shopper bought is never in a list.
- **Carts do not.** `add_to_cart` is an activity event: no pending cart turns into a purchase later. We
  never treated a cart as a pending purchase: it is a signal of interest, with the weight measured on
  our own live feedback (0.53 % per impression against 0.052 %, findings §1), and it wears off with the
  age of the cart and with repetition (findings §21, §23).
- **The catalogue carries on**: Saturday's new products stay, stock and price changes keep arriving in
  `shop.catalog_updates`. So the server must not be restarted "clean": the one running carries the state,
  and a relaunched one rebuilds the same state from the history, the journal and the feedback.

## Hard rules

- Shoppers, sessions and outcomes come from a simulator with a secret seed; the catalogue is synthetic.
  No public dataset helps.
- Feedback is private to each team. **Never share keys or feedback with other teams.**
- Recommendations must be produced by code, not by hand.
- AI coding agents and LLMs are allowed, but everything presented must be explainable by the team.
- The system must run unattended (a laptop works if it stays awake and online all night).

## Side challenge (optional): best agentic use of RawTree

Open to all teams. An AI agent that relies on RawTree to store, analyse and act on data — the agent is the
protagonist, not a wrapper. It decides what to ingest, which questions to ask and what to do with the answers
(CLI, API, SDK or MCP). Deliverable: a repo with a README and a short demo. "A small project with a great
story wins." Onboarding at the RawTree stand.

## Known inconsistency in the official material

The slides and the web page describe the baseline as "the best sellers of the **category of the last product
viewed**". The official README, the starter code and the live fallback all use the **global all-time best
sellers in stock** (verified: the `shown` lists in our fallback feedback are the top global sellers of
`shop.history_events`). Treat the README/starter definition as the real one.
