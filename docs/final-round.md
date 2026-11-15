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
- [ ] **A network cable from the laptop to the router** (the laptop has a wired port, unused so far).
      Plug it in **before the last swap of the server** and leave the Wi-Fi on. A connection stays on the
      adapter it was opened on, so a running server does not move to the cable by itself: the server
      started after the cable is in opens its connections through it (Windows prefers the wired link by
      itself), and the Wi-Fi remains as the spare. `scripts\link.ps1` says which link the server is using.
      Measured with `scripts/netmon.py`: over Wi-Fi the ping to the router averages 4-27 ms with spikes of
      100-360 ms even in good minutes (a cable gives 1 ms), and on 15 Nov at 03:16 UTC nothing crossed the
      Wi-Fi for 12 s: 34 requests unanswered, the only burst of the night (findings §24).
      **Sunday 08:40 CET: the cable at hand gave no link (the wired port never came up). The final runs
      on Wi-Fi**, which has answered 99.92 % of the requests since Saturday 21:00 CET. Leave a cable that
      gives no link unplugged: one that came and went would be worse than none.
- [ ] Leave the monitor running in a window of its own: `python scripts/netmon.py` (a few bytes per second).
      If answers are lost, `python scripts/netmon.py --report 30` says whether it was the Wi-Fi.

## Sunday, 09:00 CET — one hour before

1. Close everything that talks to the internet: OneDrive (pause syncing), Steam (it downloads updates by
   itself; it was running on the night of the 15th), Discord, browsers, Spotify, and any assistant session
   working in this repo (each of its steps uploads megabytes).
2. Network cable in, if there is one that works (see above). Then start the server — or replace the one that is running, without a
   gap — as a process of its own:

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

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\link.ps1    # "... connections to RawTree open through Ethernet"
   ```

   Healthy log line (one per minute, `$SKORE_LOGS_DIR/serve.log`):
   `answered=… failed_polls=0 failed_inserts=0 … poll_ms avg≈200 … rank_ms/request avg≈80`.

## 10:00–12:00

- **Do not touch it.** No deploys, no retraining, no experiments (AGENTS.md rule 7).
- Look at the log or run `queries/health.sql` every 15 minutes or so, and once at 10:02: at 10:00 the
  stream switches to new data. Only three things justify acting:
  - the laptop restarted, or no `python` process with `reco.serve` is left → start it again (step 2);
  - `failed_polls` / `failed_inserts` climbing fast → something is using the connection: find it and close it;
  - `queries/health.sql` shows rows `fallback / invalid`, or our light on the board turns red while the log
    looks healthy → the server is recommending products the store no longer has. It reads the catalogue
    once when it starts and follows `shop.catalog_updates` from then on (new products, prices, stock: all
    of practice came through there); a catalogue replaced without an update would not reach it. Replace
    the server (step 2): the new one reads the catalogue again. It has never happened.
- On 15 Nov one assistant session stays open to watch (Javier's decision): a local watcher on the log and
  a light check every ten minutes, nothing else. Javier authorised it to replace the server (step 2, same
  version) without asking in the first and the third case above, and in no other.
- **A drop of the connection is not one of them.** It shows as `no poll came back for 2 s` and timeouts in
  the log, and some seconds of answers missing. Do not restart the server: it goes on by itself two seconds
  after the link is back (measured, findings §24), and a restart takes longer than the drop.
  `python scripts/netmon.py --report 10` tells whether it was the Wi-Fi (router pings lost).
- The leaderboard only shows a light per team: green = more than 90 % of the last 5 minutes answered in time.

## Which version serves the final

**`skore_money_v31` alone: v9 with the trend lift in full. It has been running by itself since Sunday
06:34 CET (05:33:51 UTC).** `ARMS` in `reco/serve.py` holds that one line. No swap is owed: the only cable
at hand gave no link (Sunday 08:40 CET), so the final runs on Wi-Fi with this same server.

- Exploration **off** and no A/B in the final: every request gets the best list we have.
- Why v31. It is the best proven version, and the night's two questions were stopped with neither above
  it. They ran crossed, 25 % of the traffic each, from 00:46 to 05:33 UTC (findings §23):

  | | Requests | Purchases per 100 | Cold | Warm | EUR per request |
  |---|---|---|---|---|---|
  | **v31**: v9 + trend lift | 12,742 | 2.299 | 2.915 | 1.851 | 1.121 |
  | v38: products added during the event x1.5 (known shoppers) | 12,937 | 2.238 | 2.733 | 1.874 | 1.108 |
  | v39: v9 x organic orders the ten | 12,718 | 2.199 | 2.701 | 1.837 | 1.154 |
  | v40: both | 12,729 | 2.144 | 2.622 | 1.810 | 1.055 |

  Side against side, 25,500 requests on each: the organic order -0.10 (-1.7 se), new x1.5 -0.06 (-1.0 se).
  The rule set before the night: the organic order only if its side was not below the other over the
  night nor more than one standard error below in the minutes with a trend (it was below on both counts);
  new x1.5 only if two standard errors above. To read it again (only these minutes compare the arms:
  after them v31 runs alone):

  ```bash
  python scripts/arms.py 00:47 05:33 | python realtime_analyisi_leaderboard/pool_arms.py "v31=31" "new x1.5=38" "organic order=39" "both=40"
  python scripts/arms.py 00:47 05:33 | python realtime_analyisi_leaderboard/pool_arms.py "v9's order=31,38" "organic order=39,40"
  python scripts/arms.py 00:47 05:33 | python realtime_analyisi_leaderboard/pool_arms.py "as it is=31,39" "new x1.5=38,40"
  ```

- If Javier or Hugo want another version whatever the reading, it is one line in `ARMS`, a commit with the
  version in the message, and step 2:

  | Version | `ARMS = (…,)` |
  |---|---|
  | v31 (running) | `("skore_money_v31", "model", "v9", {"trend": 1.0}, 100)` |
  | new x1.5 | `("skore_money_v38", "model", "v9", {"trend": 1.0, "fresh": 1.5}, 100)` |
  | the organic order | `("skore_money_v39", "model", "v9o", {"trend": 1.0, "organic": 1.0, "pool": 10}, 100)` |
  | both | `("skore_money_v40", "model", "v9o", {"trend": 1.0, "organic": 1.0, "pool": 10, "fresh": 1.5}, 100)` |

  Keep the comma after a single line's closing parenthesis: `ARMS = ((…),)`.
- p95 of the answers must stay under 2,000 ms (`queries/health.sql`); v31 ranks a request in about 80 ms.
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
