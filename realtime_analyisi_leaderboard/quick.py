#!/usr/bin/env python3
"""The quarter-hour read: the gap, the latency of our answers, the arms, the server. Light on purpose.

    python realtime_analyisi_leaderboard/quick.py

Four things, in the order they matter while the system serves:
1. the latency of our answers over the last 15 minutes against the 15 before (a late answer is a lost one),
   appended to latency_history.csv;
2. the gap to the next team over 15, 30, 60 and 180 minutes (gap.py, appended to gap_history.csv);
3. the arms now serving over the same minutes, all together and with the minutes of a trend apart
   (the list of arms is experiments.py's ARMS);
4. the last lines of the server's log that say what it is doing.

Nothing heavy: the public leaderboard API, one small query on the team's feedback, the tail of a local log.
Stdlib only.
"""
from __future__ import annotations

import csv
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
sys.path.insert(0, str(HERE))
import experiments  # noqa: E402
import gap  # noqa: E402
from rt import load_env, query  # noqa: E402

LATENCY = """
SELECT if(ts::DateTime64(3) > now() - INTERVAL 15 MINUTE, 'last 15 min', 'the 15 before') AS window, count() AS requests,
       countIf(served_by != 'team') AS not_by_us,
       round(quantileIf(0.5)(latency_ms::Float64, served_by = 'team')) AS p50, round(quantileIf(0.95)(latency_ms::Float64, served_by = 'team')) AS p95,
       round(quantileIf(0.99)(latency_ms::Float64, served_by = 'team')) AS p99, countIf(served_by = 'team' AND latency_ms::Float64 > 3000) AS over_3s
FROM {team}.feedback WHERE ts > now() - INTERVAL 30 MINUTE GROUP BY window ORDER BY window"""


def main() -> None:
    load_env()
    now = int(time.time())
    end = now - now % 300
    print(f"== {datetime.fromtimestamp(now, timezone.utc):%H:%M:%S} UTC ({experiments.hhmm(now, 1)} CET)")

    rows = query(LATENCY.format(team=os.environ["TEAM_ID"]))["data"]
    print("\n1) LATENCY of our answers (ms) — a late answer is a lost one")
    for r in rows:
        print(f"   {r['window']:<14} requests {int(r['requests']):>5}  not by us {int(r['not_by_us']):>3}  p50 {float(r['p50']):.0f}  p95 {float(r['p95']):.0f}  "
              f"p99 {float(r['p99']):.0f}  over 3 s {int(r['over_3s'])}")
    log = Path(os.environ.get("SKORE_LOGS_DIR", HERE.parent / "logs")) / "serve.log"
    status, trend, started = "", "", 0
    if log.exists():
        lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
        stamp = ""
        for i, ln in enumerate(lines, 1):
            if re.match(r"\d\d:\d\d:\d\d answered=", ln):
                status, stamp = ln, ln[:8]
            elif ln.startswith("trend:"):
                trend = f"{stamp} {ln}"
            elif ln.startswith("serving ["):
                started = i
    rank = re.search(r"rank_ms/request avg=(\d+) max=(\d+)", status)
    poll = re.search(r"poll_ms avg=(\d+) max=(\d+)", status)
    last = next((r for r in rows if r["window"] == "last 15 min"), None)
    if last:
        path = HERE / "latency_history.csv"
        new = not path.exists()
        with path.open("a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["utc", "requests", "not_by_us", "p50_ms", "p95_ms", "p99_ms", "over_3s", "rank_ms_avg", "rank_ms_max", "poll_ms_avg", "poll_ms_max"])
            w.writerow([f"{datetime.fromtimestamp(now, timezone.utc):%Y-%m-%d %H:%M}", int(last["requests"]), int(last["not_by_us"]), int(float(last["p50"])),
                        int(float(last["p95"])), int(float(last["p99"])), int(last["over_3s"])] + list(rank.groups() if rank else ("", "")) + list(poll.groups() if poll else ("", "")))

    print("\n2) GAP to the next team")
    gap.main()

    print("\n3) ARMS now serving, same minutes")
    common = max(experiments.epoch(s) for _, _, s in experiments.ARMS)
    total = experiments.read(common, end)
    suffixes = [s for s, _, _ in experiments.ARMS]
    for regime, title in (("all", "all minutes"), ("rest", "no trend"), ("trend", "trend minutes")):
        rows_ = total[regime]
        if "reference" not in rows_ or suffixes[0] not in rows_:
            continue
        ref, _ = experiments.values(rows_["reference"])
        first = experiments.values(rows_[suffixes[0]])
        print(f"   {title} since {experiments.hhmm(common)} UTC — reference {ref['all']:.3f} / cold {ref['cold']:.3f} / warm {ref['warm']:.3f}")
        for s in suffixes:
            if s not in rows_:
                continue
            v, n = experiments.values(rows_[s])
            against = "" if s == suffixes[0] else "  vs v" + suffixes[0] + ": " + ", ".join(
                f"{k} {v[k] - first[0][k]:+.2f} ({(v[k] - first[0][k]) / (experiments.SPREAD[k] * (1 / max(n[k], 1) + 1 / max(first[1][k], 1)) ** 0.5):+.1f} se)"
                for k in ("all", "cold", "warm"))
            print(f"     v{s}  requests {n['all']:>6,}  overall {v['all']:.3f} ({v['all'] - ref['all']:+.3f})  cold {v['cold']:.3f}  warm {v['warm']:.3f}  "
                  f"eur {v['eur']:.2f}{against}")
        for line in experiments.contrast_lines(rows_):
            print(f"     > {line}")

    print("\n4) SERVER")
    print(f"   last start at log line {started}; last trend line: {trend or 'none'}")
    print(f"   {status[:220]}")


if __name__ == "__main__":
    main()
