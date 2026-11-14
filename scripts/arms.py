#!/usr/bin/env python3
"""Compare model versions with the organisers' own metric (stdlib only).

    python scripts/arms.py                       # our versions, last 60 minutes
    python scripts/arms.py 15:10 15:40           # a window in UTC, today (15 min to 3 h, 5-minute steps)
    python scripts/arms.py 15:10 15:40 --all     # every team's versions with enough traffic

The leaderboard API (`/api/state?by=model&from=..&to=..`) reports, per `model_version`, the EXPECTED
purchases per 100 requests according to the hidden model — the number the final is scored on, without the
coin flip of realised purchases. For an A/B that is about 3× less noisy than counting purchases in our
feedback, so it is how we decide between versions that ran over the same minutes.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

URL = "https://datathon.rawtree.dev/api/state"
ROOT = Path(__file__).resolve().parent.parent


def team_id() -> str:
    if "TEAM_ID" in os.environ:
        return os.environ["TEAM_ID"]
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            key, _, value = line.partition("=")
            if key.strip() == "TEAM_ID":
                return value.strip()
    return ""


def fetch(start: int, end: int) -> dict:
    req = urllib.request.Request(f"{URL}?by=model&from={start}&to={end}", headers={"User-Agent": "datathon-agent/arms.py"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def hhmm(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%H:%M:%S")


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    now = int(time.time())
    end = now - now % 300
    start = end - 3600
    if len(args) == 2:
        day = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        start, end = (int(day.replace(hour=int(a[:2]), minute=int(a[3:5])).timestamp()) for a in args)
    state = fetch(start, end)
    ref, base = state["reference"], state["baseline"]
    print(f"{hhmm(state['window'][0])}–{hhmm(state['window'][1])} UTC · expected purchases per 100 requests · "
          f"reference {ref['conversion']:.3f} (cold {ref['cold_conversion']:.3f}) · baseline {base['conversion']:.3f}")
    me, everyone = team_id(), "--all" in sys.argv
    print(f"{'team':<9} {'model_version':<28} {'requests':>8} {'conv':>6} {'cold':>6} {'cold req':>8} {'€/req':>6}  active (UTC)")
    rows = [(t["team_id"], v) for t in state["teams"] for v in (t.get("versions") or [])
            if t["team_id"] == me or (everyone and v["requests"] >= 300)]
    for team, v in sorted(rows, key=lambda r: (r[0] != me, -r[1]["conversion"])):
        print(f"{team:<9} {str(v.get('model_version')):<28} {v['requests']:>8} {v['conversion']:6.3f} "
              f"{(v.get('cold_conversion') or 0):6.3f} {v.get('cold_requests', 0):>8} {v.get('revenue_per_request', 0):6.3f}  "
              f"{hhmm(v['first'])}–{hhmm(v['last'])}")


if __name__ == "__main__":
    main()
