#!/usr/bin/env python3
"""Refresh the numbers the deck shows (stdlib only, read-only, no API key needed).

    python3 presentation/update_data.py     # → presentation/data.js

Reads the public leaderboard (https://datathon.rawtree.dev/api/state) and the trend kept by the watch
session (realtime_analyisi_leaderboard/history.csv), and writes them as one JavaScript object that
index.html loads. Run it once the final ranking is published (Sun 12:00 CET) and the "where we stand"
slide shows the final round instead of the practice round.

While the final is running the leaderboard hides every metric: the script then leaves data.js untouched.
"""
from __future__ import annotations

import csv
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

URL = "https://datathon.rawtree.dev/api/state"
HERE = Path(__file__).resolve().parent
HISTORY = HERE.parent / "realtime_analyisi_leaderboard" / "history.csv"
TEAM = os.environ.get("TEAM_ID", "team_06")
KEEP = ("conversion", "cold_conversion", "on_time", "revenue_per_request", "model_version")


def row(team: dict) -> dict:
    return {k: team.get(k) for k in KEEP}


def trend() -> list[list[float]]:
    """[unix seconds, our conversion, reference, baseline] per tick of the practice round, oldest first."""
    points: dict[int, list[float]] = {}
    if HISTORY.exists():
        with open(HISTORY, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["mode"] != "practice":
                    continue
                t = int(datetime.strptime(r["utc"], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).timestamp())
                points[t] = [t, float(r["conv"]), float(r["ref_conv"]), float(r["base_conv"])]
    return [points[t] for t in sorted(points)]


def main() -> None:
    with urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "deck"}), timeout=20) as r:
        state = json.load(r)
    teams = state.get("teams", [])
    rank = next((i for i, t in enumerate(teams) if t.get("team_id") == TEAM), None)
    if rank is None or teams[rank].get("conversion") is None:
        sys.exit(f"mode={state.get('mode')}: no metrics for {TEAM} right now; data.js left as it was")

    history = trend()
    if state["mode"] == "practice":     # the tick of this very minute, so the chart ends where the slide does
        history.append([int(state["updated_at"]), teams[rank]["conversion"],
                        state["reference"]["conversion"], state["baseline"]["conversion"]])
    data = {
        "mode": state["mode"],
        "updated_at": int(state["updated_at"]),
        "rank": rank + 1,
        "teams": len(teams),
        "team": row(teams[rank]),
        "rivals": [row(t) for i, t in enumerate(teams) if i != rank][:2],   # the two best other teams
        "reference": row(state["reference"]),
        "baseline": row(state["baseline"]),
        "history": history,
    }
    (HERE / "data.js").write_text(
        "// Written by update_data.py from the public leaderboard. Do not edit by hand.\n"
        f"window.DECK_DATA = {json.dumps(data, indent=1)};\n", encoding="utf-8")
    print(f"data.js: mode={data['mode']} rank={data['rank']}/{data['teams']} "
          f"conversion={data['team']['conversion']:.2f} (reference {data['reference']['conversion']:.2f}, "
          f"baseline {data['baseline']['conversion']:.2f}), {len(history)} trend points")


if __name__ == "__main__":
    main()
