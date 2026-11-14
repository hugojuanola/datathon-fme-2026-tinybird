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
- [ ] If there is a cable: plug the laptop into the router. Wi-Fi was fine when nothing else used it.

## Sunday, 09:00 CET — one hour before

1. Close everything that talks to the internet: OneDrive (pause syncing), Discord, browsers, Spotify,
   and any assistant session working in this repo (each of its steps uploads megabytes).
2. Start the server in its own window, so it depends on nothing else:

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\run_server.ps1
   ```

   If a server is already running, replace it without a gap instead: add `-Standby`, wait for
   `standby: ready` in the log, stop the old one, then create the `GO` file the log names.
3. Check it (each command is one small query):

   ```bash
   python scripts/rt.py -f queries/health.sql        # last 10 min: everything served_by = team, p95 < 2000 ms
   python scripts/arms.py                            # our versions, organisers' own metric
   python scripts/leaderboard.py                     # the light must be GREEN during the final
   ```

   Healthy log line (one per minute, `$SKORE_LOGS_DIR/serve.log`):
   `answered=… failed_polls=0 failed_inserts=0 … poll_ms avg≈200 … rank_ms/request avg≈50`.

## 10:00–12:00

- **Do not touch it.** No deploys, no retraining, no experiments (AGENTS.md rule 7).
- Look at the log or run `queries/health.sql` every 15 minutes or so. Only two things justify acting:
  - the window with `run_server.ps1` was closed or the laptop restarted → start it again (step 2);
  - `failed_polls` / `failed_inserts` climbing fast → something is using the connection: find it and close it.
- The leaderboard only shows a light per team: green = more than 90 % of the last 5 minutes answered in time.

## Which version serves the final

- Exploration **off**: no `explore` arm in `ARMS` (reco/serve.py). It is a practice-round tool.
- One arm, the best version by `scripts/arms.py` over a long same-minutes window in practice. No A/B in
  the final: every request should get the best list we have.
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
