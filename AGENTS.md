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
| [`scripts/arms.py`](scripts/arms.py) | **How we judge an A/B**: expected purchases per 100 requests per `model_version` (the organisers' own metric), cold and warm, over any window |
| [`scripts/netmon.py`](scripts/netmon.py) | Router ping and RawTree connect time once per second: tells Wi-Fi from the rest when answers are lost |
| [`scripts/swap_server.ps1`](scripts/swap_server.ps1), [`reco/supervise.py`](reco/supervise.py), [`docs/final-round.md`](docs/final-round.md) | Start or replace the live server without a gap. It runs with **no window** under a supervisor that restarts it (it does not die with a terminal or an assistant session, and there is nothing to close by mistake); the runbook for the final |
| [`best_model.md`](best_model.md) | The best proven version, the line that puts it back, what is being measured against it, and the log of improvements |
| [`reco/`](reco/) | **Our recommender**: `serve.py` (live loop), `state.py` (event-sourced live state), `features.py` (the one definition of every model feature, shared by training and serving), `recommend.py` (policies: rules, and rules-retrieve + model-rank), `rawtree.py` (client), `priority.py` |
| [`offline/`](offline/) | Offline work: `pull_data.py` (export history / live stream), `build_dataset.py` (training table by replaying the store in time order), `train.py` (LightGBM click + conversion models, validated on the future), `evaluate.py` (policies on the held-out last week), `build_cache.py` (start-up cache for the server), `store_moves.py` (trends, price changes and new products in the organic stream, aggregated in RawTree, and the live trend detector replayed on them) |
| [`models/`](models/) | The trained ranker (`click.txt`, `conv.txt`: LightGBM text models, readable) |
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

python -m venv <somewhere outside any synced folder> && <venv>/Scripts/pip install requests numpy pandas pyarrow scipy lightgbm scikit-learn
<venv>/Scripts/python -m reco.serve --dry                                  # our recommender, printing instead of inserting
<venv>/Scripts/python -u -m reco.serve >> $SKORE_LOGS_DIR/serve.log 2>&1   # our recommender, LIVE (one instance only)
```

Deploying a new version **without a gap** (never two instances answering at once), one command:

```bash
powershell -ExecutionPolicy Bypass -File scripts/swap_server.ps1
# starts the new server in standby as a process of its own, waits for "standby: ready" and a clean
# self-test in the log, stops the old one, creates $SKORE_LOGS_DIR/GO. If the new one is not fit, nothing changes.
```

Retraining (all offline scripts lower their own priority so they do not starve the server):

```bash
<venv>/Scripts/python -m offline.pull_data live      # refresh the live stream export (events + our feedback)
<venv>/Scripts/python -m offline.build_dataset       # training table: one row per (request, product shown)
<venv>/Scripts/python -m offline.train NAME          # models/NAME + validation report (last week of log, last quarter of live)
<venv>/Scripts/python -m offline.train NAME 20       # same, a live row counting as 20 log rows: the ranker for cold requests
<venv>/Scripts/python -m offline.store_moves         # how the store moved today, and how the trend detector saw it (8 s)
<venv>/Scripts/python -m offline.evaluate            # policies on the held-out week, through the live code
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
9. **Nothing heavy on the serving machine while it serves.** On 14 Nov 13:14–13:31 UTC we lost 25 % of the
   answers three times: a second process loading its state with big RawTree queries, a model scoring the
   whole catalogue with every core, and OneDrive uploading hundreds of MB of data files over a ~100 KB/s
   uplink (the repo lives in a synced folder). So: bulky files go to `$SKORE_DATA_DIR` / `$SKORE_LOGS_DIR`
   outside any synced folder; offline scripts call `reco.priority.background()`; new versions start with
   `--standby`; and during the final, pause OneDrive and run nothing else. Details: `docs/findings.md` §8.

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

As of Sun 15 Nov 2026 01:50 CET (branch `javier`): **`reco/serve.py` is running live** from Javier's laptop,
answering in about 1.0 s (p95 1.5-2.2 s). What a request goes through:

1. **Retrieve** — the rules (`score_rules`): popularity x measured lifts, 1,000 candidates.
2. **Rank** — two LightGBM models, `P(click) x P(purchase | click)`, over the features of
   `reco/features.py` (counts, shares and matches: never an id). Requests are routed by kind: a ranker
   written `"v9w|v9"` sends the cold ones (new shopper, or a product added during the event among the recent
   views) to the first ranker and the rest to the second. Not in use: one ranker serves everybody (three
   measurements against weighting live feedback x20 for cold requests). Optionally a third model multiplies
   the score: the organic propensity, "this shopper is about to buy this product in the store".
3. **Store moves** — the trend detector (`reco.features.Trends`, fed from `shop.events` every second)
   multiplies the scores of a trending subcategory by its lift (measured live: a trend sells x8.3 in our
   carousel, the detector says x8.6).
4. **Hard rules** — never a product the shopper already bought, never one out of stock.

Arms (`ARMS` in `reco/serve.py`, tagged in `model_version`), one ranker for every request, 25 % of the traffic
each since 01:46 CET on Sunday. Two questions crossed, so that each is read on all the traffic:
`skore_money_v31` v9 + full trend lift, the version to beat · `v38` v31 with the score of a product added
during the event x1.5 for known shoppers · `v39` v9 + lift picks the ten and v9 x the organic model
(`models/v9o`, `offline/organic.py`) only orders them: the same ten products as v31, and the one use of the
organic model measured offline (+2.5 % purchases, findings §22) · `v40` both. "The organic order" is
(v39 + v40) against (v31 + v38); "new x1.5" is (v38 + v40) against (v31 + v39). No exploration.
In the arms with the organic model a trending product keeps the rank v9 and the lift give it and the
organic factor orders only the other products (findings §23: with a neutral factor it was losing the first
slot); in every arm, a product added during the event stays out of the lists for its first 20 minutes (it
is not clicked before: findings §22). Closed on the way: v32 and v36 (the organic factor choosing among
v9's best 100: never above v31, slower), v33 to v35, v37 (v39 before the trending products kept their rank).
Evidence for every piece: [`docs/findings.md`](docs/findings.md) (§15 how an A/B is judged and what the
versions scored, §16 trends / prices / new products, §18 reliability, §19 a faster offline judge, §20 the
organic model and the arms of the night, §21 ten signals checked against what v9 already predicts, the lift
for new products and the organic factor during a trend, §22 the organic model as a second stage, §23 the first read of the night and the arms as two questions
crossed). The store's calendar (trends, promotions, new
products) is in [`docs/data.md`](docs/data.md). A second session writes a live read of the board and
of each arm in [`realtime_analyisi_leaderboard/`](realtime_analyisi_leaderboard/README.md).

Where we stand (Sunday 01:50 CET, last hour): first with 2.37 expected purchases per 100 requests; next
teams 2.25 (team_17), 2.22 (team_03) and 2.18 (team_42); the organisers' reference about 2.0. Cold requests
3.09 against 2.96 for the next team. `on_time` 99.9 %. The gap over the second team has been between 0.07
and 0.17 all night; the second session logs it every 15 minutes.

Open for the final (the humans decide, before Sunday 09:30 CET; findings §20 has the design):
1. **Read the night**: the three commands in [`docs/final-round.md`](docs/final-round.md) (`scripts/arms.py
   00:47 07:30` UTC, piped into `pool_arms.py`), or the table in `best_model.md`. v31 is the version to
   beat. A change goes into the final only if its side is 2 standard errors above the other over the whole
   night and not below it in the minutes with a trend (45 minutes from :30 of every odd UTC hour); for the
   organic order, look at the money per request too. One night can show harm or a gain above 4 %, not a
   gain of 2.5 % (findings §23): if nothing passes, v31 serves the final. The first hours (22:25 to 00:46
   UTC, arms v31, v32, v36, v37) are in findings §23.
   **If a reading shows us off first place before the final** (standing order from Javier, 15 Nov 00:15 CET:
   recover it as fast as possible, hold it, widen the gap). The second session reads the board every 15
   minutes and raises the alarm when we are not first on the 60-minute window (a 15-minute window is noise:
   three arms running the same code read 1.92, 2.40 and 2.59 in one). The answer, in this order:
   reliability first (`queries/health.sql`: lost or late answers are the fastest points to lose and to win
   back); then an arm 2 standard errors below the others over a clean window is taken out; then, if a rival
   has simply improved, the traffic goes to our best arm by the longest clean window, with 20 % kept for
   the comparison. From 08:00 CET on, nothing changes on the server without Javier or Hugo (rule 7).
2. **A single arm** for the final with the winner (`scripts/swap_server.ps1` after editing `ARMS`):
   [`docs/final-round.md`](docs/final-round.md). If nobody chooses, what is running is a sound mix: every
   arm is v9 or a step or two from it, and all the traffic has the lift.
3. **The connection.** A network cable to the router, nothing else using the line, no assistant session
   open on the laptop during the two hours. `scripts/netmon.py` is logging to tell Wi-Fi from the rest.

Local setup of this laptop: `SKORE_DATA_DIR` / `SKORE_LOGS_DIR` point to `C:/Users/javil/skore_money/`
(outside OneDrive) and the Python environment is `C:/Users/javil/skore_money/venv` (not `.venv` in the repo:
OneDrive was uploading it). Only one `reco.serve` may answer at a time (rule 4). The live server is
started only by `scripts/swap_server.ps1`: no window (`pythonw -m reco.supervise` and its child `python -m
reco.serve` in Task Manager), it survives closing the assistant app and restarts itself. At 18:53 UTC on
14 Nov a version that still had a console window was closed by mistake: four minutes without answers.
Never start a server as a child of an assistant session or in a window. Commit at every deploy,
with the `model_version` in the message, so the repository always matches what is serving. Update this
section when that changes.
