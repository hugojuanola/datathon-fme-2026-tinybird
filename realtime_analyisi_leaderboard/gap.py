#!/usr/bin/env python3
"""How far ahead of the next team are we? The board over the last 15, 30, 60 and 180 minutes (stdlib only).

    python realtime_analyisi_leaderboard/gap.py            # prints, and appends a row to gap_history.csv
    python realtime_analyisi_leaderboard/gap.py --dry      # prints only

For each window: our place among the teams, our expected purchases per 100 requests, the best other team and
the gap to it, the same on cold requests (the cold-start points), the reference, and our share of requests
answered on time. The short windows say where we are now, the long one whether it lasts; a gap of less than
about 0.1 on 15 minutes is inside what two identical recommenders differ by.

Read-only and light: four calls to the public leaderboard API.
"""
from __future__ import annotations

import csv
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

URL = "https://datathon.rawtree.dev/api/state"
HERE = Path(__file__).resolve().parent
ME = "team_06"
WINDOWS = (15, 30, 60, 180)


def fetch(start: int, end: int) -> dict:
    req = urllib.request.Request(f"{URL}?from={start}&to={end}", headers={"User-Agent": "datathon-agent/gap.py"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def main() -> None:
    now = int(time.time())
    end = now - now % 300
    row = {"utc": datetime.fromtimestamp(end, timezone.utc).strftime("%Y-%m-%d %H:%M")}
    print(f"board to {row['utc']} UTC — expected purchases per 100 requests")
    print(f"{'window':>7} {'place':>5} {'us':>6} {'next team':>9} {'theirs':>6} {'gap':>7} | {'cold us':>7} {'best other':>10} {'cold gap':>8} | {'ref':>5} {'on time':>7}")
    for minutes in WINDOWS:
        state = fetch(end - 60 * minutes, end)
        if state.get("mode") not in (None, "practice"):
            print(f"{minutes:>5} m  the board is hidden (mode {state.get('mode')})")
            continue
        teams = {t["team_id"]: t for t in state["teams"]}
        us = teams.get(ME)
        if not us:
            continue
        others = sorted((t for k, t in teams.items() if k != ME), key=lambda t: -(t.get("conversion") or 0))
        cold = max(others, key=lambda t: t.get("cold_conversion") or 0)
        conv, nxt = us.get("conversion") or 0.0, others[0]
        place = 1 + sum((t.get("conversion") or 0) > conv for t in others)
        gap, cold_gap = conv - (nxt.get("conversion") or 0), (us.get("cold_conversion") or 0) - (cold.get("cold_conversion") or 0)
        print(f"{minutes:>5} m {place:>5} {conv:6.3f} {nxt['team_id']:>9} {nxt.get('conversion') or 0:6.3f} {gap:+7.3f} | "
              f"{us.get('cold_conversion') or 0:7.3f} {cold['team_id']:>10} {cold_gap:+8.3f} | {state['reference'].get('conversion') or 0:5.2f} "
              f"{us.get('on_time') or 0:6.1f}%")
        row.update({f"place_{minutes}m": place, f"conv_{minutes}m": round(conv, 4), f"next_{minutes}m": nxt["team_id"],
                    f"next_conv_{minutes}m": round(nxt.get("conversion") or 0, 4), f"gap_{minutes}m": round(gap, 4),
                    f"cold_gap_{minutes}m": round(cold_gap, 4), f"ref_{minutes}m": round(state["reference"].get("conversion") or 0, 4)})
    if "--dry" not in sys.argv and len(row) > 1:
        path = HERE / "gap_history.csv"
        new = not path.exists()
        with path.open("a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(row))
            if new:
                w.writeheader()
            w.writerow(row)


if __name__ == "__main__":
    main()
