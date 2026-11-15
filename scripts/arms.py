#!/usr/bin/env python3
"""Compare model versions with the organisers' own metric (stdlib only).

    python scripts/arms.py                       # our versions, last 60 minutes
    python scripts/arms.py 15:10 15:40           # a window in UTC, today (5-minute steps, at least 15 minutes)
    python scripts/arms.py 21:30 07:30           # a start later than the end means yesterday evening → today
    python scripts/arms.py 22:25 23:30           # a window that has not begun yet (run after midnight) is yesterday's
    python scripts/arms.py 15:10 15:40 --all     # every team's versions with enough traffic

The leaderboard API (`/api/state?by=model&from=..&to=..`) reports, per `model_version`, the EXPECTED
purchases per 100 requests according to the hidden model — the number the final is scored on, without the
coin flip of realised purchases. It serves windows of up to 3 hours and at most 10 versions per team in one
answer, so a long window is read in pieces and added up (every figure is an average per request: pieces are
weighted by their requests), and a piece that comes back with versions missing is read again in halves.

How much to trust a difference: two arms running the SAME code on ~1,550 requests each differed by 0.12
(14 Nov, 16:45-17:12 UTC), and three-arm quarters of an hour swing by ±0.3. Judge on hours, not minutes.
"cold" = new shopper, or a product added during the event among the recent views (10 of the 70 points);
"warm" = the rest, derived here from the two published numbers.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

URL = "https://datathon.rawtree.dev/api/state"
ROOT = Path(__file__).resolve().parent.parent
PIECE = 3 * 3600


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


class Sum:
    """Requests-weighted totals of one row (a model version, the reference, the baseline) across pieces."""

    def __init__(self) -> None:
        self.requests = self.cold_requests = 0
        self.buys = self.cold_buys = self.revenue = 0.0
        self.first, self.last = float("inf"), 0.0

    def add(self, row: dict, requests: int | None = None) -> None:
        n = row.get("requests") or requests or 0
        cold = row.get("cold_requests") or 0
        self.requests += n
        self.cold_requests += cold
        self.buys += n * (row.get("conversion") or 0.0)
        self.cold_buys += cold * (row.get("cold_conversion") or 0.0)
        self.revenue += n * (row.get("revenue_per_request") or 0.0)
        self.first, self.last = min(self.first, row.get("first") or self.first), max(self.last, row.get("last") or 0.0)

    def line(self, team: str, name: str) -> str:
        n, cold = max(self.requests, 1), self.cold_requests
        warm = (self.buys - self.cold_buys) / (n - cold) if cold and n > cold else float("nan")
        active = f"{hhmm(self.first)}–{hhmm(self.last)}" if self.last else ""
        return (f"{team:<9} {name:<28} {self.requests:>8} {self.buys / n:6.3f} {self.cold_buys / max(cold, 1):6.3f} "
                f"{warm:6.3f} {cold:>8} {self.revenue / n:6.3f}  {active}")


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    now = int(time.time())
    end = now - now % 300
    start = end - 3600
    if len(args) == 2:
        day = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        a, b = (day.replace(hour=int(x[:2]), minute=int(x[3:5])) for x in args)
        if a >= b:
            a -= timedelta(days=1)
        if a.timestamp() > now:      # not begun yet: yesterday's (the API would answer with the last minutes)
            a, b = a - timedelta(days=1), b - timedelta(days=1)
        start, end = int(a.timestamp()), min(int(b.timestamp()), end)
    me, everyone = team_id(), "--all" in sys.argv
    rows: dict[tuple[str, str], Sum] = {}
    ref, base = Sum(), Sum()
    lo = hi = None
    pieces = [(a, min(a + PIECE, end)) for a in range(start, end, PIECE)]
    while pieces:
        a, b = pieces.pop(0)
        state = fetch(a, b)
        cut = max((t.get("more_versions") or 0 for t in state["teams"] if t["team_id"] == me or everyone), default=0)
        if cut and b - a >= 1800:      # versions left out of the answer: read this piece in two halves instead
            mid = a + (b - a) // 2 // 300 * 300
            pieces[:0] = [(a, mid), (mid, b)]
            continue
        if cut:
            print(f"warning: {hhmm(a)}–{hhmm(b)} still leaves {cut} version(s) out", file=sys.stderr)
        lo, hi = (state["window"][0] if lo is None else lo), state["window"][1]
        # every team gets every request: the share of cold ones is read from our own versions
        traffic = max((t.get("requests") or 0 for t in state["teams"]), default=0)
        ours = [v for t in state["teams"] if t["team_id"] == me for v in (t.get("versions") or [])]
        cold_share = sum(v.get("cold_requests") or 0 for v in ours) / max(sum(v.get("requests") or 0 for v in ours), 1)
        for row, total in ((state["reference"], ref), (state["baseline"], base)):
            n = row.get("requests") or traffic
            total.add({**row, "requests": n, "cold_requests": round(cold_share * n)})
        for t in state["teams"]:
            for v in t.get("versions") or []:
                if t["team_id"] == me or everyone:
                    rows.setdefault((t["team_id"], str(v.get("model_version"))), Sum()).add(v)
    if abs(lo - start) > 300 or abs(hi - end) > 300:     # too short a window, or one the API does not keep
        print(f"warning: asked for {hhmm(start)}–{hhmm(end)}, the API answered for {hhmm(lo)}–{hhmm(hi)}", file=sys.stderr)
    print(f"{hhmm(lo)}–{hhmm(hi)} UTC · expected purchases per 100 requests")
    print(f"{'team':<9} {'model_version':<28} {'requests':>8} {'conv':>6} {'cold':>6} {'warm':>6} {'cold req':>8} {'€/req':>6}  active (UTC)")
    print(ref.line("", "reference"))
    print(base.line("", "baseline"))
    shown = [(k, s) for k, s in rows.items() if k[0] == me or s.requests >= 300 * max(1, (end - start) // 900)]
    for (team, name), s in sorted(shown, key=lambda r: (r[0][0] != me, -r[1].buys / max(r[1].requests, 1))):
        print(s.line(team, name))


if __name__ == "__main__":
    main()
