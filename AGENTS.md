# AGENTS.md — start here

Briefing for any AI agent (or human) working in this repo. Read this file fully, then open the linked
document for whatever you are about to touch.

## Mission

We are team **Skore Money** (`team_06`: Hugo Juanola, Javier Aranda) at **Datathon FME 2026**, doing the
**Tinybird RawTree challenge: real-time recommendation**.

A shopper arrives at an online store ~3 times per second. For each one we have **3 seconds** to write an
ordered list of **10 product IDs** into RawTree. A hidden simulator decides clicks and purchases. We win by
selling more than the "best sellers" baseline, measured live. **Our running system is the submission.**

## Deadlines (Barcelona time, CET = UTC+1 — all data timestamps are UTC)

| When | What |
|---|---|
| Sat 14 Nov 10:00 → Sun 15 Nov 10:00 | Practice round. Public leaderboard. **Does not count.** Experiment freely. |
| **Sun 15 Nov 10:00 → 12:00** | **Final round: the only scored window (70 points).** New shoppers, products and trends. Leaderboard hidden. |
| Sun 15 Nov 14:00 | Presentation + demo to the jury (30 points). |

The best version must be running, unattended, **before Sunday 10:00 CET (09:00 UTC)**.

## Where everything is

| Path | What |
|---|---|
| [`docs/challenge.md`](docs/challenge.md) | Rules, submission format, timeline, scoring, jury criteria |
| [`docs/data.md`](docs/data.md) | Every table: schema, gotchas, and numbers measured on the live data |
| [`docs/rawtree.md`](docs/rawtree.md) | RawTree cheat sheet: API, SQL on Dynamic columns, limits, MCP/CLI |
| [`docs/event.md`](docs/event.md) | Team, links, event schedule |
| [`docs/sources/`](docs/sources/README.md) | Verbatim official material (brief, web page, slides, schedule) — ground truth |
| [`docs/rawtree/`](docs/rawtree/) | 30 vendored RawTree doc pages |
| [`.claude/skills/rawtree/`](.claude/skills/rawtree/SKILL.md) | Official RawTree agent skill |
| [`starter/`](starter/) | Official starter kit, unmodified: baseline loop, SQL examples, offline-eval notebook |
| [`scripts/rt.py`](scripts/rt.py) | Run SQL against RawTree from the shell (stdlib, read-only by default) |
| [`scripts/leaderboard.py`](scripts/leaderboard.py) | Print the public leaderboard |
| [`reco/`](reco/) | **Our recommender**: `serve.py` (live loop), `state.py` (live state from RawTree), `recommend.py` (ranking policy), `rawtree.py` (client) |
| [`offline/`](offline/) | Offline work: `pull_data.py` exports the history to `data/` (git-ignored); `evaluate.py` validates the policy on the held-out last week |
| [`docs/findings.md`](docs/findings.md) | What drives a purchase, measured: the evidence behind the ranking policy |
| [`queries/`](queries/) | Our reusable SQL: `health.sql` (is the live system healthy?), `variants.sql` (A/B by `model_version`), `tiers.sql` (which ranking tier sells) |
| [`avanced_data_analysis/`](avanced_data_analysis/README.md) | Exploratory analysis: distributions, outliers, PCA/UMAP/clustering, SHAP importance — what drives purchases, with figures and the request→feedback workflow diagram |
| `.env` | `TEAM_ID` and `RAWTREE_API_KEY`. **Git-ignored. Not in the repo.** Template: [`.env.example`](.env.example) |

## Setup and everyday commands

```bash
cp .env.example .env          # then fill in TEAM_ID=team_06 and the key (ask a teammate; never commit it)

python3 scripts/rt.py "SELECT count() FROM shop.requests"                 # any SQL; `team_NN` → team_06
python3 scripts/rt.py -f queries/health.sql --stats                       # from a file, with rows/bytes read
python3 scripts/leaderboard.py                                            # where we stand

python -m venv .venv && .venv/Scripts/pip install requests numpy pandas pyarrow duckdb lightgbm scikit-learn
.venv/Scripts/python -m reco.serve --dry                                  # our recommender, printing instead of inserting
.venv/Scripts/python -u -m reco.serve >> logs/serve.log 2>&1              # our recommender, LIVE (one instance only)
```

Is the system healthy? (last 10 minutes of our feedback: who served, conversion, latency)

```bash
python3 scripts/rt.py -f queries/health.sql
```

Healthy = almost everything `served_by = 'team'`, p95 latency well under 3000 ms.

## How we are scored — what to optimise

- **Conversion, 50 pts**: expected purchases per 100 requests (the simulator's purchase probability for the
  10 products shown — no luck involved).
- **Cold start, 10 pts**: the same, only on requests where `is_new_user = true` or `recent_views` contains
  a product added during the event.
- **Reliability, 10 pts**: share of requests answered validly and on time.
- Conversion and cold start are scaled between the **baseline** (0) and the **oracle** (100).
  Tie-breaker: expected revenue per request.
- **Jury, 30 pts**: method validated offline (10), learning from the stream (10), use of RawTree (5),
  communication (5).

Reference points from the practice leaderboard: baseline ≈ 0.72 purchases / 100 requests, organisers'
reference recommender ≈ 2.24. Details in [`docs/challenge.md`](docs/challenge.md).

## Non-negotiable rules

1. **Never commit, print, log or paste `RAWTREE_API_KEY`.** It lives only in `.env`. Before every commit
   run `git diff --cached | grep -nE "rt_[a-z0-9]{12,}_[0-9a-f]{16,}"` and make sure it prints nothing. Do not send the key, team
   feedback or user data to any third-party service. The jury will read this repo.
2. **Every answer is exactly 10 distinct product IDs that are active and in stock right now.** One bad ID
   invalidates the whole answer. Stock changes every 5 minutes; new products appear during the event.
3. **Answer within 3 s of the request `ts`** (organisers' clock). Budget: a request is visible ~0.3 s after
   its `ts`, the baseline answers at ~1 s. Batch inserts (every 0.3–0.5 s), never one HTTP call per request.
4. **One answer per request, from one process.** Never run two recommenders against `team_06.submissions`
   at the same time — only one answer counts and we do not control which.
5. **The loop must never die.** Catch everything, keep answering with the last good model, and fall back
   to a safe list (in-stock best sellers) rather than to nothing. An unanswered request scores as fallback
   *and* costs reliability.
6. **Recommendations come from code, never by hand.** And the team must be able to explain every piece of
   it to the jury: prefer approaches you can justify over clever ones you cannot.
7. **Do not disturb the live system close to or during the final** (Sun 10:00–12:00 CET) without an
   explicit go-ahead from Hugo or Javier. Before that window, restart/redeploy freely.
8. **`rt.py` is read-only unless `--write`.** Writes to `team_06.submissions` affect our live score;
   `TRUNCATE` / `DROP` / `DELETE` on anything need explicit human approval.

## Ways of working

- **Validate offline before going live.** Hold out the last days of `shop.history_sessions`, compare
  against the baseline (hit rate, IPS/SNIPS — see `starter/offline_eval.ipynb`), then deploy and confirm
  with real feedback. This is literally 10 of the jury points; keep the evidence (numbers, plots) in the repo.
- **Tag every deployed variant** with a distinct `model_version` — it is stored with each submission, shown
  on the leaderboard, and lets us compare variants in `team_06.feedback`.
- **Measure on live feedback.** Realised purchases are noisy (≈1 purchase per 100 requests, 3 requests/s):
  judge a change on thousands of requests, not on a few minutes.
- **Generalise, do not memorise.** The final round uses unseen shoppers, products and trends. Anything keyed
  only on known `user_id`s or known `product_id`s will be absent exactly where the cold-start points are.
- **Use RawTree for real work** (features in SQL, `team_06.scratch`, workflows): it is scored, and the
  history is too big to pull raw (12 M rows; 30 s query cap).
- **Keep the repo readable**: small modules, a README that tells the story, no dead experiments left around.
- Docs and code in English. The team speaks Spanish — answer them in the language they write in.
- When you learn a durable fact about the data or the platform, add it to the matching file in `docs/`
  (with the date it was measured) so the next agent does not have to rediscover it.

## Facts worth having in your head

- Every RawTree column is `Dynamic`: **cast join keys and aggregate arguments** (`product_id::String`,
  `ts::DateTime64(3)`, `price_eur::Float64`).
- ~5,000 products, 10 categories, 89 subcategories, 80 brands; +100 new products appeared 1 h into practice.
- Requests: 30% `is_new_user`; 20% are `home` page with **no** `recent_views`; the rest have 1–6 recent views.
- Historical conversion: `product`/`category` pages ≈ 1.7%, `home` ≈ 0.14%. Slot 1 gets 6.6× the clicks of slot 10.
- A shopper only buys the product they clicked; a shopper who already bought a product tends not to want it again.
- Feedback for a request lands ≈ 4.2 s after its `ts`. `clicked`/`purchased` are `''` when nothing happened
  (but `NULL` in the historical sessions).
- Fallback = global all-time best sellers in stock (not per category, whatever the slides say).

Full detail and the queries behind these numbers: [`docs/data.md`](docs/data.md).

## State of the repo

As of Sat 14 Nov 2026 13:45 CET (branch `javier`): **`reco/serve.py` v4 is running live** from Javier's
laptop, answering every request in ≈1.1 s (p95 ≈ 1.8 s). The policy (`reco/recommend.py`) scores every
product as `popularity × lifts` (category and subcategory of the last view, abandoned cart, just viewed),
never shows a product the shopper already bought, and A/B-tests the "just viewed" lift (`model_version`
`v4a` = ×3, `v4b` = ×1.5). Evidence and offline validation: [`docs/findings.md`](docs/findings.md).
First live read: ≈2.6 % conversion for the ×3 arm vs 0.79 % baseline (small sample).
Next: replace the hand-set lifts with a learned ranker (LightGBM on the log + live feedback), gated by
`python -m offline.evaluate`. Only one `reco.serve` may run at a time (rule 4): check
`queries/health.sql` before starting another. Update this section when that changes.
