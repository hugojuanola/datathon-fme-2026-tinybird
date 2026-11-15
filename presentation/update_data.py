#!/usr/bin/env python3
"""Refresh the numbers the deck shows (stdlib only, read-only, no API key needed).

    python3 presentation/update_data.py     # → presentation/data.js

Reads the public leaderboard (https://datathon.rawtree.dev/api/state) and the trend kept by the watch
session (realtime_analyisi_leaderboard/history.csv), and writes them as one JavaScript object that
index.html loads. Run after the final (Sun 15 Nov, 12:00 CET), it writes the final ranking, and the "where
we stand" slide shows the final round instead of the practice round. It also keeps the organisers' score of
every hour (`hours`: ours, our place and the leader's), from the public `progress` series.

It also rebuilds the public board of the practice round every 5 minutes (the API serves any window: about
290 small requests, a minute) to say since when we lead it and for how long we did not: `lead` in data.js.

While the final is running the leaderboard hides every metric: the script then leaves data.js untouched.
"""
from __future__ import annotations

import csv
import json
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

URL = "https://datathon.rawtree.dev/api/state"
HERE = Path(__file__).resolve().parent
HISTORY = HERE.parent / "realtime_analyisi_leaderboard" / "history.csv"
TEAM = os.environ.get("TEAM_ID", "team_06")
KEEP = ("conversion", "cold_conversion", "on_time", "revenue_per_request", "model_version",
        "requests", "score", "conversion_score", "cold_score")
BOARD_WINDOW = 3600     # the public board ranks on the last hour


def row(team: dict) -> dict:
    return {k: team.get(k) for k in KEEP}


def trend() -> list[list[float]]:
    """[unix seconds, our conversion, reference, baseline] per tick of the practice round, oldest first
    (in final mode main() adds the final as one more point, at its close)."""
    points: dict[int, list[float]] = {}
    if HISTORY.exists():
        with open(HISTORY, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["mode"] != "practice":
                    continue
                t = int(datetime.strptime(r["utc"], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).timestamp())
                points[t] = [t, float(r["conv"]), float(r["ref_conv"]), float(r["base_conv"])]
    return [points[t] for t in sorted(points)]


def hours(state: dict) -> list[list]:
    """[hour start (unix s), our score, our place, the leader's score, the leader] per hour, from `progress`."""
    progress = {team: dict(map(tuple, points)) for team, points in (state.get("progress") or {}).items()}
    out = []
    for t in sorted({t for points in progress.values() for t in points}):
        board = sorted(((points.get(t, 0), team) for team, points in progress.items()), reverse=True)
        place = next((i + 1 for i, (_, team) in enumerate(board) if team == TEAM), None)
        if place:
            out.append([int(t), progress[TEAM][t], place, board[0][0], board[0][1]])
    return out


def final_progress(state: dict, place: int) -> dict | None:
    """Our place in the final every 5 minutes (the organisers' anonymised view), and the gap to the first."""
    try:
        view = fetch("?view=progress")
    except (OSError, ValueError):
        return None
    teams = view.get("teams") or []
    ours = next((t for t in teams if t.get("team") == TEAM), None) or \
        next((t for t in teams if t.get("ranks") and t["ranks"][-1] == place), None)
    if not ours:
        return None
    return {"checkpoints": [int(c) for c in view["checkpoints"]], "ranks": ours["ranks"],
            "gap_leader": ours.get("gap_leader"), "start": int(state["final_start"]), "end": int(state["final_end"])}


def fetch(query: str = "") -> dict:
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(URL + query, headers={"User-Agent": "deck"}), timeout=40) as r:
                return json.load(r)
        except OSError:
            if attempt == 2:
                raise
            time.sleep(1 + attempt)


def lead(state: dict) -> dict:
    """Since when we lead the public board of the practice round, and for how long we did not since then.

    The board as it was at every step (5 minutes) of the practice round: the last hour up to that moment, in
    the organisers' own order. `since` is the first of those moments with us on top.
    """
    start, step = int(state["practice_start"]), int(state["limits"]["step"])
    end = min(int(time.time()), int(state["final_start"]))
    moments = list(range(start + int(state["limits"]["min"]), end + 1, step))

    def place(t: int) -> int | None:
        begin = max(start, t - BOARD_WINDOW)
        board = fetch(f"?from={begin}&to={t}")
        if [round(x) for x in board.get("window") or []] != [begin, t]:
            raise ValueError(f"the API did not serve the window ending at {t}")
        ids = [team.get("team_id") for team in board.get("teams") or []]
        return ids.index(TEAM) + 1 if TEAM in ids else None

    with ThreadPoolExecutor(3) as pool:
        places = list(pool.map(place, moments))
    first = places.index(1)                                   # ValueError if we never led: no `lead` then
    after = places[first:]
    return {
        "since": moments[first],
        "until": moments[-1],
        "minutes_not_first": sum(p != 1 for p in after) * step // 60,
        "minutes_off_podium": sum(p is None or p > 3 for p in after) * step // 60,
    }


def previous_lead() -> dict | None:
    try:
        text = (HERE / "data.js").read_text(encoding="utf-8")
        return json.loads(text[text.index("{"):text.rindex("}") + 1]).get("lead")
    except (OSError, ValueError):
        return None


def main() -> None:
    state = fetch()
    teams = state.get("teams", [])
    rank = next((i for i, t in enumerate(teams) if t.get("team_id") == TEAM), None)
    if rank is None or teams[rank].get("conversion") is None:
        sys.exit(f"mode={state.get('mode')}: no metrics for {TEAM} right now; data.js left as it was")

    history = trend()
    if state["mode"] == "practice":     # the tick of this very minute, so the chart ends where the slide does
        history.append([int(state["updated_at"]), teams[rank]["conversion"],
                        state["reference"]["conversion"], state["baseline"]["conversion"]])
    if state["mode"] == "final":        # the final's two hours, as one point at its close
        history.append([int(state["final_end"]), teams[rank]["conversion"],
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
        "hours": hours(state),
    }
    if state["mode"] == "final":
        data["final"] = final_progress(state, rank + 1)
    try:
        data["lead"] = lead(state)
    except (OSError, ValueError, KeyError) as e:      # e.g. after the final, if the API no longer serves the practice
        data["lead"] = previous_lead()
        print(f"lead: not recomputed ({e}); kept the one already in data.js", file=sys.stderr)
    (HERE / "data.js").write_text(
        "// Written by update_data.py from the public leaderboard. Do not edit by hand.\n"
        f"window.DECK_DATA = {json.dumps(data, indent=1)};\n", encoding="utf-8")
    print(f"data.js: mode={data['mode']} rank={data['rank']}/{data['teams']} "
          f"conversion={data['team']['conversion']:.2f} (reference {data['reference']['conversion']:.2f}, "
          f"baseline {data['baseline']['conversion']:.2f}), {len(history)} trend points")
    if data["lead"]:
        at = lambda t: datetime.fromtimestamp(t, timezone.utc).strftime("%a %H:%M UTC")
        print(f"lead: first since {at(data['lead']['since'])} (up to {at(data['lead']['until'])}), "
              f"except {data['lead']['minutes_not_first']} min; off the podium {data['lead']['minutes_off_podium']} min")


if __name__ == "__main__":
    main()
