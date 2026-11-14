# 14 Nov, 14:14–14:22 CET — incident: a quarter of the requests went unanswered

**What happened.** For eight minutes the live server answered late or not at all. Practice round, so no
points lost — but this is the failure that would cost the 10 reliability points and conversion on Sunday.

| 2-minute bucket (UTC) | Requests | Fallback (`missing`) | p50 latency | p95 latency |
|---|---|---|---|---|
| 13:00–13:12 | 360 each | 0 | 1.10 s | 1.6 s |
| 13:14 | 360 | 99 | 1.20 s | 2.7 s |
| 13:16 | 360 | 42 | 1.44 s | 2.8 s |
| 13:18 | 360 | 107 | 1.82 s | 3.2 s |
| 13:20 | 360 | 64 | 1.82 s | 3.1 s |
| 13:22 onwards | 360 | 0 | — | 2.1 s |

`logs/serve.log` during the incident: `insert failed, retrying: Read timed out (read timeout=2.5)`,
`loop error: Read timed out (read timeout=3)`, loop time 1.9 s (normally 0.2–0.5 s), `skipped_late` 4 → 44.

**Cause, as far as the process list shows.** The laptop that serves was also running a heavy local job. At
14:21 a Python process (`live_check.py`, 51 threads, 971 MB) was using 57% of all CPU while `reco.serve` had
24 threads; OneDrive sync was using another ≈25% (the repository is inside a OneDrive folder, so every log,
parquet and model file written is synced). A trivial RawTree query from the same machine took its usual
time, so the API was not the bottleneck. The fallbacks began at 13:14 UTC, six minutes before `live_check.py`
started, so an earlier job (dataset build or training) had the same effect. It recovered at 13:22 UTC.

**What to change before the final.**

1. The serving machine serves and nothing else. Training, dataset builds and heavy checks go to another
   machine (Javier offered Google Colab).
2. If something must run locally, cap it: LightGBM `num_threads=2`, low process priority.
3. Keep models, parquet files and logs outside the OneDrive folder, or pause OneDrive during the final.
4. Alarm on the loop time: a line in the log (and in `tick.py`) when it exceeds one second.
5. The leaderboard's `on_time` covers one hour, so a restart or a stall shows for an hour: plan restarts.

## Update, 14:45 CET — root cause and fix, from the session that owns the server

The stall lasted until about 14:31 CET. Two causes: (1) a dry run and a test script that loaded the state with
heavy RawTree aggregations and scored the 5,100 products on all cores; (2) OneDrive uploading about 550 MB of
exports and logs written inside the repository, over an uplink of roughly 100 KB/s. Fixed in commit `ffad8c3`:
data and logs now live outside the repository (`SKORE_DATA_DIR`, `SKORE_LOGS_DIR` in `.env`), the server starts
from a local cache and journal instead of heavy SQL, a new server takes over with `--standby`, offline scripts
lower their priority and the server raises its own. Since 14:35 CET: p50 1.05 s, p95 1.4 s, no unanswered
requests apart from the 38 lost in the switch to v5.

On the analysis side: the EDA cache moved out of the repository as well, and `tick.py` no longer scans
`shop.history_events`.

## Update, 15:02 CET — a second, shorter stall at 14:58–15:01

After the hand-over to v5 + exploration at 14:57:00 CET (itself clean: no request lost), fallbacks per 20 seconds:

| 20 s starting (UTC) | 13:58:00 | 13:58:20 | 13:59:20 | 14:00:00 | 14:00:20 | 14:00:40 | 14:01:00 | 14:01:20 |
|---|---|---|---|---|---|---|---|---|
| Unanswered, of 60 | 6 | 11 | 7 | 53 | 39 | 40 | 16 | 0 |

172 requests lost in three minutes. The server log shows `slow_loops` growing by 8 a minute from its first
minute, then at 15:00:00 CET all three refreshers timing out at once (`refresh_feedback`, `refresh_catalog`,
`refresh_events`, read timeout 5 s) and connection timeouts to the API.

What it was not: a RawTree outage — team_09, team_01 and team_20 stayed at 99.6–99.8% on time. So it is local
to our laptop or our key. Not established: whether it is the server's own fast polling around the 5-minute
mark, another local process, or this watch — a tick ran at 13:59:05–13:59:30 UTC and two small diagnostic
queries at about 14:00:15, overlapping the stall without clearly preceding it.

Changes on the watch side, in case it contributes: one tick per 15 minutes instead of two runs, never within
a minute of a 5-minute mark, no extra diagnostic queries while the server is unhealthy.
