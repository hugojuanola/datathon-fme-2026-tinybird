# Final round runbook — Sunday 15 Nov, 10:00–12:00 CET (09:00–11:00 UTC)

The brief: "Your system *is* your submission: whatever it answers between 10:00 and 12:00 is what gets
scored" and "Your system has to run unattended: keep it running on a machine that will not go to sleep."
Nobody runs our model for us: for those two hours our process must be alive, on a connection that works,
answering every request within 3 s. **It runs on Javier's laptop** (decided 14 Nov).

What cost us answers during practice was never the model (it ranks in ~50 ms): it was the laptop's
connection being busy with something else (docs/findings.md §8). So the checklist is mostly about that.

## The evening before

- [ ] Decide the version that will serve the final (see "Which version" below) and leave it running.
- [ ] Windows: Settings → System → Power → *Screen and sleep* → "When plugged in, put my device to sleep
      after: **Never**". The server also asks Windows not to sleep while it runs, but closing the lid or a
      forced update restart is stronger than that: lid open, charger in.
- [ ] Windows Update: *Pause updates* for a week (a restart at 10:30 would be the end of it).
- [ ] **A network cable from the laptop to the router.** Measured with `scripts/netmon.py` on 14 Nov: over
      Wi-Fi the ping to the router averages 11-27 ms with spikes of 100-360 ms even in good minutes (a cable
      gives 1 ms), and the bursts of lost answers are stalls of every connection at once.
- [ ] Leave the monitor running in a window of its own: `python scripts/netmon.py` (a few bytes per second).
      If answers are lost, `python scripts/netmon.py --report 30` says whether it was the Wi-Fi.

## Sunday, 09:00 CET — one hour before

1. Close everything that talks to the internet: OneDrive (pause syncing), Discord, browsers, Spotify,
   and any assistant session working in this repo (each of its steps uploads megabytes).
2. Start the server — or replace the one that is running, without a gap — as a process of its own:

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\swap_server.ps1
   ```

   It starts a new server in standby, waits until it has loaded and passed its self-test (every arm answers
   real requests: all lines must read `N/N valid lists`), and only then stops the old one and gives the GO;
   if anything is wrong the old one keeps answering. With no server running it simply starts one. The
   server it starts has **no window**: it is the two `python` processes with `reco.serve` in their command
   line (Task Manager → Details) plus a `pythonw` supervisor that starts it again if it ever exits. It
   hangs from Windows itself and not from a terminal, an editor or an assistant session, and there is no
   window to close (on Saturday at 18:53 UTC a console window with the server in it was closed by mistake:
   four minutes without answers). After a restart of the laptop, run the command again.
3. Check it (each command is one small query):

   ```bash
   python scripts/rt.py -f queries/health.sql        # last 10 min: everything served_by = team, p95 < 2000 ms
   python scripts/arms.py                            # our versions, organisers' own metric
   python scripts/leaderboard.py                     # the light must be GREEN during the final
   ```

   Healthy log line (one per minute, `$SKORE_LOGS_DIR/serve.log`):
   `answered=… failed_polls=0 failed_inserts=0 … poll_ms avg≈200 … rank_ms/request avg≈80`.

## 10:00–12:00

- **Do not touch it.** No deploys, no retraining, no experiments (AGENTS.md rule 7).
- Look at the log or run `queries/health.sql` every 15 minutes or so. Only two things justify acting:
  - the laptop restarted, or no `python` process with `reco.serve` is left → start it again (step 2);
  - `failed_polls` / `failed_inserts` climbing fast → something is using the connection: find it and close it.
- The leaderboard only shows a light per team: green = more than 90 % of the last 5 minutes answered in time.

## Which version serves the final

- Exploration **off**: no `explore` arm in `ARMS` (reco/serve.py). It is a practice-round tool.
- One arm, the best version by `scripts/arms.py` over a long same-minutes window in practice. No A/B in
  the final: every request should get the best list we have. Reading the night and setting the arm:

  ```bash
  python scripts/arms.py 00:47 07:30 | python realtime_analyisi_leaderboard/pool_arms.py "v9's order=31,38" "organic order=39,40"
  python scripts/arms.py 00:47 07:30 | python realtime_analyisi_leaderboard/pool_arms.py "as it is=31,39" "new x1.5=38,40"
  python scripts/arms.py 00:47 07:30 | python realtime_analyisi_leaderboard/pool_arms.py "v31=31" "new x1.5=38" "organic order=39" "both=40"
  ```

  (UTC: Sunday 01:47 to 08:30 CET; the last column is each group against the first, in standard errors.)
  Since 00:46 UTC the four arms are two questions crossed, 25 % of the traffic each, so that each question
  is read on all of it, half on each side:

  | | v9's order | v9 x organic orders the ten |
  |---|---|---|
  | **as it is** | v31, the version to beat | v39 |
  | **products added during the event x1.5** (known shoppers) | v38 | v40 |

  The rule, one question at a time: **a change goes into the final only if its side is at least 2 standard
  errors above the other side over the whole night and not below it in the minutes with a trend** (45
  minutes from :30 of every odd UTC hour: `arms.py 01:30 02:15`, `03:30 04:15`, `05:30 06:15`). For the
  organic order also look at the money per request (the tie-breaker, `EUR/req` in `arms.py`): before
  midnight the three arms with the organic model earned 1.12 to 1.26 EUR per request against 1.34 for v31.
  Then leave a single line in `ARMS` (`reco/serve.py`) at 100 %, commit it, and replace the running server
  as in step 2 (`scripts\swap_server.ps1`):

  | What passed | `ARMS = (…,)` |
  |---|---|
  | nothing | `("skore_money_v31", "model", "v9", {"trend": 1.0}, 100)` |
  | new x1.5 | `("skore_money_v38", "model", "v9", {"trend": 1.0, "fresh": 1.5}, 100)` |
  | the organic order | `("skore_money_v39", "model", "v9o", {"trend": 1.0, "organic": 1.0, "pool": 10}, 100)` |
  | both | `("skore_money_v40", "model", "v9o", {"trend": 1.0, "organic": 1.0, "pool": 10, "fresh": 1.5}, 100)` |

  What one night can tell: with 36,000 requests on each side the standard error of a difference is 0.05
  purchases per 100 requests, so 2 standard errors are 0.10, about 4 % of what we sell. The offline
  estimates are smaller than that (+2.5 % for the organic order, findings §22; less for the x1.5, which
  touches few lists, §21), so the likely reading is "level, within a standard error or two", and then
  v31 serves the final: it is the proven one. What the night does settle is harm: a side that is clearly
  below is out. None of the four costs time (the organic model is asked about ten products: 2 ms
  more than v31 per answer); p95 of the answers must stay under 2,000 ms (`queries/health.sql`).
  The best proven version and the line that puts it back are in [`best_model.md`](../best_model.md).
- The model must not depend on having seen the shopper before: the final brings new shoppers, products
  and trends. What carries over, by construction: features are counts, shares and matches (never ids);
  a shopper's profile is built from the live stream within minutes; a new product is described by its
  attributes, subcategory and price from the first second (findings §11, §13, §14).

## If the laptop cannot be used after all

Any machine with Python 3.12 works (a small cloud VM near AWS us-east-1 would even be faster: RawTree's
router is there). On it: clone the repo, create `.env`, then

```bash
pip install requests numpy pandas pyarrow scipy lightgbm scikit-learn
python -m offline.pull_data          # history export, ~1 min
python -m offline.build_cache        # start-up cache, ~1 min
python -m reco.serve --standby       # loads, catches up with the live stream, waits for the GO file
```

and hand over as in step 2. Never two servers answering at once.
