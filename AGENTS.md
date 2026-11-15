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
| [`scripts/netmon.py`](scripts/netmon.py), [`scripts/link.ps1`](scripts/link.ps1) | Router ping and RawTree connect time once per second: tells Wi-Fi from the rest when answers are lost · which link (cable or Wi-Fi) the live server's connections leave through |
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

As of Sun 15 Nov 2026 08:50 CET (branch `javier`): **`reco/serve.py` is running live** from Javier's laptop,
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

**One arm since 06:34 CET on Sunday (05:33:51 UTC), and for the final: `skore_money_v31`**, v9 with the trend
lift in full, for every request (`ARMS` in `reco/serve.py`). It is the best proven version and nothing
measured against it came out above. The night's two questions ran crossed, 25 % of the traffic each, from
01:46 to 06:33 CET, 25,500 requests on each side: a product added during the event x1.5 for known shoppers
(`v38`) read -0.06 (-1.0 se), and v9 + lift picking the ten with v9 x the organic model (`models/v9o`,
`offline/organic.py`) ordering them (`v39`; `v40` was both) read -0.10 (-1.7 se), where held-out lists had
given +2.5 % ± 1.1. They were stopped when neither could reach its bar by the morning any more and two
rivals had drawn level with us on the 30-minute board with half of our traffic on the lower side: Javier's
standing order (the traffic to our best arm), without an arm kept for a comparison because no question was
left that the remaining hours could answer (findings §23). Their lines are in the comment above `ARMS`.
No exploration. A product added during the event stays out of the lists for its first 20 minutes (it is
not clicked before: findings §22). Closed earlier: v32 and v36 (the organic factor choosing among v9's
best 100: never above v31, slower), v33 to v35, v37 (v39 before the trending products kept their rank).
Evidence for every piece: [`docs/findings.md`](docs/findings.md) (§15 how an A/B is judged and what the
versions scored, §16 trends / prices / new products, §18 reliability, §19 a faster offline judge, §20 the
organic model and the arms of the night, §21 ten signals checked against what v9 already predicts, the lift
for new products and the organic factor during a trend, §22 the organic model as a second stage, §23 the
night's two questions crossed, how they ended and what they say about the held-out estimate, the trends of
the night and a trend too small for the detector, §24 twelve seconds without Wi-Fi and what the loop did).
The store's calendar (trends, promotions, new products) is in [`docs/data.md`](docs/data.md). A second
session writes a live read of the board and of our version in
[`realtime_analyisi_leaderboard/`](realtime_analyisi_leaderboard/README.md).

Where we stand. On the public board's last hour at 08:29 CET we are first, 2.255 against 2.231 for team_03, and
on the organisers' score for 07:00 to 08:00 CET, the first whole hour of v31 alone, 63.5 against 62.8.
Earlier (07:22 CET, v31 alone for 47 minutes of each window): first on the 15- and
30-minute boards by 0.015, second on the 60-minute one by 0.006 (team_03 2.189), first on the 180-minute
one by 0.049. On the organisers' hourly score we led by 2 to 4 points from 03:00 to 06:00 CET (62.5 to
63.9) and in the hour to 07:00 CET it read team_03 63.6, team_14 62.8, us 62.7. **The three leaders are
level.** Outside trends the best version of each of the nearest teams reads like v31 or a little above
(2.27 to 2.38 against 2.12 to 2.22 in the last three half hours, within one standard error each time and
on the same side each time); their team numbers are held down by a second version each, which they may
drop for the final. Our lead is made in the trends: the lift is worth about 0.08 on the board while a
trend of ordinary size runs (inside Sneakers the gap was +0.13 against +0.06 before it), and its dose sat
on the prediction in three trends. A trend moves the board in proportion to its share of the store's
purchases: the one on a tiny subcategory (Watches, 06:30 CET: 37 purchases in 45 minutes) is at the edge
of the detector, which went on and off 19 times, and moved nothing for anybody; the detector is unchanged
(findings §23). Where nobody has caught the organisers' reference is on requests from known shoppers
(2.05 to 2.19 against our 1.84 to 1.98, and 1.84 to 1.94 for the nearest teams): the headroom we did not
find (findings §23). Answers on time: 100 % except the 34 of 04:16 CET (findings §24) and the 6 of each
swap. The second session logs the board every 15 minutes, reports to Javier from 08:00 CET and stops at
09:30 CET, so that no assistant session is open during the final.

For the final (Javier or Hugo, before 09:30 CET):
1. **The version is already running**: v31 alone since 06:34 CET. To serve another one, its line is in
   [`docs/final-round.md`](docs/final-round.md), but nothing measured supports it. Javier's standing order
   (15 Nov 00:15 CET: if a reading shows us off first place, recover it as fast as possible, hold it, widen
   the gap) has been applied as far as it goes: reliability first, then the traffic to our best arm. There
   is no better arm of ours left to move to; what holds the place from here is answering every request.
   From 08:00 CET on, nothing changes on the server without Javier or Hugo (rule 7).
2. **No swap is owed: the final runs on Wi-Fi.** The only cable at hand was tried at 08:40 CET and gave no
   link (the wired port never came up), so nothing was changed. The server that serves the final is the
   one started at 06:33 CET (v31 alone, no failed poll or insert since), on the link that has answered
   99.92 % of 124,900 requests since Saturday 21:00 CET. A drop like the one of 04:16 CET would cost about
   0.1 of the 100 points and has happened once in 14.6 hours (findings §24). Had the cable worked: a
   running server keeps the connections it has, so it would have taken a swap (`scripts\link.ps1` shows
   which link the server uses).
3. **The connection.** Nothing else using the line (OneDrive paused, Steam and browsers closed).
   `scripts/netmon.py` is logging to tell Wi-Fi
   from the rest. On Sunday at 03:16 UTC nothing crossed the Wi-Fi for 12 s and 34 requests went
   unanswered, the only burst of the night; the server resumed by itself and only about three of them were
   within reach of a different loop, so the loop is unchanged (findings §24). Never restart the server
   because of a network drop.

4. **One assistant session stays open during the final, to watch** (Javier's decision, 15 Nov 08:55 CET;
   through the night two sessions worked without a pause and the answers on time stayed at 100 %). It
   runs nothing heavy: a local watcher on `serve.log` that wakes it on failed polls or inserts, a restart
   or a log that stops growing, and one light check every ten minutes (processes, last status line, the
   connection monitor, `queries/health.sql`). No analysis, no push, no change of model or `ARMS`.
   **Authorised by Javier (15 Nov 09:00 CET), without asking him first: relaunch the server with
   `scripts\swap_server.ps1`, same version, in two cases only**: (a) no server process is left and the
   supervisor has not brought one back within a minute; (b) answers come back `fallback / invalid`
   (the catalogue changed in a way the stream did not announce). A drop of the connection is neither:
   the server resumes by itself. Anything else is reported to Javier and waits for him.

Local setup of this laptop: `SKORE_DATA_DIR` / `SKORE_LOGS_DIR` point to `C:/Users/javil/skore_money/`
(outside OneDrive) and the Python environment is `C:/Users/javil/skore_money/venv` (not `.venv` in the repo:
OneDrive was uploading it). Only one `reco.serve` may answer at a time (rule 4). The live server is
started only by `scripts/swap_server.ps1`: no window (`pythonw -m reco.supervise` and its child `python -m
reco.serve` in Task Manager), it survives closing the assistant app and restarts itself. At 18:53 UTC on
14 Nov a version that still had a console window was closed by mistake: four minutes without answers.
Never start a server as a child of an assistant session or in a window. Commit at every deploy,
with the `model_version` in the message, so the repository always matches what is serving. Update this
section when that changes.
