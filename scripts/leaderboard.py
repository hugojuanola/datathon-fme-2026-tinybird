#!/usr/bin/env python3
"""Print the public leaderboard (stdlib only). Source: https://datathon.rawtree.dev/api/state

    python3 scripts/leaderboard.py           # table, our team marked with '>'
    python3 scripts/leaderboard.py --json    # raw state JSON

The state refreshes every 10 minutes and, during practice, ranks on the last hour.
Modes: waiting · practice · final_running (only a green/red light per team) · final.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

URL = "https://datathon.rawtree.dev/api/state"
TZ = ZoneInfo("Europe/Madrid")
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


def hhmm(ts: float) -> str:
    return datetime.fromtimestamp(ts, TZ).strftime("%a %H:%M")


def main() -> None:
    req = urllib.request.Request(URL, headers={"User-Agent": "datathon-agent/leaderboard.py"})
    with urllib.request.urlopen(req, timeout=20) as r:
        s = json.loads(r.read())
    if "--json" in sys.argv:
        print(json.dumps(s, indent=2))
        return
    me = team_id()
    print(f"mode={s['mode']}  updated {hhmm(s['updated_at'])}  next {hhmm(s['next_update'])}  (Barcelona time)")
    print(f"practice from {hhmm(s['practice_start'])} · final {hhmm(s['final_start'])} → {hhmm(s['final_end'])}")
    if s["mode"] == "final_running":
        for light in s.get("lights") or []:
            mark = ">" if light["team_id"] == me else " "
            print(f"{mark} {light['team_id']:<10} {'GREEN' if light['green'] else 'RED'}")
        return
    teams = s.get("teams") or []
    if not teams:
        print("no teams yet")
        return
    show_score = not s.get("hidden")
    head = f"  {'#':>2} {'team':<10} " + (f"{'score':>7} " if show_score else "") + f"{'conv%':>7} {'cold%':>7} {'on_time%':>8} {'€/req':>7} {'requests':>8}  model"
    print(head)

    def line(mark: str, rank: str, r: dict, with_score: bool) -> str:
        score = f"{r.get('score', 0):7.3f} " if show_score and with_score else (" " * 8 if show_score else "")
        return (f"{mark} {rank:>2} {r['team_id']:<10} {score}{r['conversion']:7.4f} {r['cold_conversion']:7.4f} "
                f"{r['on_time']:8.1f} {r['revenue_per_request']:7.3f} {r.get('requests', 0):8d}  {r.get('model_version', '')}")

    for i, r in enumerate(teams, 1):
        print(line(">" if r["team_id"] == me else " ", str(i), r, True))
    for name in ("reference", "baseline"):
        if s.get(name):
            print(line(" ", "", s[name], False))


if __name__ == "__main__":
    main()
