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

## Update, 15:10 CET — the cause of both stalls, from the session that owns the server

The Python environment (`.venv`, 669 MB) was inside the repository, and the repository is inside OneDrive.
OneDrive had been uploading it since 13:15 CET at a steady ≈110 KB/s, which is the whole uplink of this
connection. With the uplink full, any extra traffic from the laptop pushed the serving loop into read and
connect timeouts: each stall coincided with a second process talking to RawTree (dry runs at 14:14, 14:20
and 14:59–15:01 CET). The watch tick was probably not the cause.

What changed: the environment moved to `C:/Users/javil/skore_money/venv` (outside OneDrive), like the data
and the logs before it; the server now uses three staggered pollers and two senders, so one slow call no
longer blocks the loop.

For the final, in order of importance:

1. **Pause OneDrive on the serving laptop** for the whole final, and check the uplink is idle before 10:00.
2. Nothing bulky inside the repository folder: environment, data, models and logs live outside it.
3. Nothing else that talks to RawTree from this laptop during the final, apart from the server and, at most,
   one light watch tick away from the 5-minute marks.

## Update, 15:32 CET — the uplink is not capped at 110 KB/s

Upload measured every second for a minute (14:29:08–14:30:12 UTC, OneDrive closed, Wi-Fi 5 GHz at 80% signal
and 866 Mbps link rate, so the Wi-Fi itself is not the limit):

- a **floor of about 100–130 KB/s that never stops** — something on the laptop uploads continuously;
- **bursts of 300–800 KB/s lasting 2–10 seconds**, several per minute (for example 297 → 702 KB/s during
  14:29:45–14:29:54, 794 at 14:29:58, 413–551 at 14:30:05).

So the line carries at least 0.8 MB/s up; the earlier reading of "a 110 KB/s uplink" was the floor, not the
ceiling. What competes with the server is the continuous sender plus the bursts. The bursts line up with the
moments a Claude session sends a request (each step uploads the whole conversation, megabytes for a long
one); the continuous sender was not identified from here — Task Manager → Processes → sort by "Network"
shows it. The server's own traffic is small (about 20 KB/s).

For the final the conclusion is the same, with a clearer reason: the machine and the connection that serve
should carry nothing else — no calls or screen sharing, no cloud sync, no long-running assistant sessions.
The safest form of that is to serve from a dedicated machine.

## Update, 20:15 CET — a four-minute outage: the server's console window was closed

723 requests went unanswered between 18:53 and 18:57 UTC (119, 180, 180, 180 and 64 per minute).

**Cause**, established by the session that owns the server: at 18:53:15 UTC the Windows Terminal window
titled "Skore Money recommender - leave this window open" was closed by hand. `serve.log` ends with a
`KeyboardInterrupt` in the main loop at that second, and the supervising loop lived in the same window, so
nothing restarted the server. Nobody noticed for three and a half minutes; then `scripts\swap_server.ps1`
loaded a server in 30 seconds and it answered at 18:57:15 UTC with the same arms.

The hand-over between versions was not involved: the last real swap, at 18:34:26 UTC, lost 2 requests.

**What it cost on the board**: `on_time` over the last 15 minutes fell to 73.2 %, and that window read
1.766 expected purchases per 100 requests against the reference's 1.960.

**For the final**: the server must not live in a window that can be closed (a windowless supervisor, since
done in `reco/supervise.py`, live from 20:11 CET), and a whole minute without answers should raise an alarm
at once rather than wait for somebody to look.
