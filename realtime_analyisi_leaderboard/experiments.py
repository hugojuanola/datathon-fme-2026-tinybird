#!/usr/bin/env python3
"""Refresh the live part of experiments.md: where we stand, and how the arms now serving compare, by regime.

    python realtime_analyisi_leaderboard/experiments.py

experiments.md is the ledger of every test we ran: what it asked, what came out, what it gives, what it
costs, and the verdict. Its tables are written by hand when a test closes. Between the two `live` markers
this script rewrites, every hour: the gap to the next team on four windows, the official hourly score, and
the arms now serving read on the organisers' metric over the same minutes, with the minutes of a trend and
the rest apart (a trend runs for 45 minutes from :30 of every odd UTC hour: the store's calendar, used here
to read, never inside the recommender).

The arms and the minute each one counts from are in ARMS below: update it when the server's arms change.
Read-only and light: the public leaderboard API. Stdlib only.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
import arms as board  # noqa: E402  (scripts/arms.py: the per-version reader of the leaderboard API)

URL = "https://datathon.rawtree.dev/api/state"
ME = "team_06"
# (version suffix, what it is, the UTC minute it counts from)
ARMS = [("31", "v9 + trend lift, alone on all the traffic: the version for the final", "2026-11-15 05:35")]
# the questions the arms are crossed on, each read on all the traffic: (name, the arms with it, the arms without).
# None while one arm serves alone. The night of 15 Nov (00:50-05:30 UTC) ran four arms with
#   ARMS suffixes 31, 38, 39, 40 and
#   ("the organic order (v39 + v40) against v9's order (v31 + v38)", ("39", "40"), ("31", "38")),
#   ("new products x1.5 (v38 + v40) against none (v31 + v39)", ("38", "40"), ("31", "39"));
# its whole read is written out in experiments.md, section 2.
CONTRASTS: list[tuple[str, tuple[str, ...], tuple[str, ...]]] = []
SPREAD = {"all": 6.5, "cold": 8.8, "warm": 4.75}     # per request, between arms running the same code (14 Nov)
START, END = "<!-- live:start -->", "<!-- live:end -->"


def epoch(text: str) -> int:
    return int(datetime.strptime(text, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).timestamp())


def hhmm(ts: int, shift: int = 0) -> str:
    return (datetime.fromtimestamp(ts, timezone.utc) + timedelta(hours=shift)).strftime("%H:%M")


def pieces(start: int, end: int) -> list[tuple[int, int, bool]]:
    """[start, end) cut into the minutes of a trend and the rest; pieces under 15 minutes are left out."""
    out, t = [], start
    while t < end:
        k = (t - 5400) // 7200                      # trends start at 01:30, 03:30, ... UTC and last 45 minutes
        s = k * 7200 + 5400
        if s <= t < s + 2700:
            b, trend = min(s + 2700, end), True
        else:
            b, trend = min(s + 7200, end), False
        if b - t >= 900:
            out.append((t, b, trend))
        t = b
    return out


def read(start: int, end: int) -> dict:
    """{regime: {version suffix or 'reference': Sum}} for our versions over [start, end)."""
    total = {r: {} for r in ("trend", "rest", "all")}
    for a, b, trend in pieces(start, end):
        state = board.fetch(a, b)
        traffic = max((t.get("requests") or 0 for t in state["teams"]), default=0)
        ours = [v for t in state["teams"] if t["team_id"] == ME for v in (t.get("versions") or [])]
        cold_share = sum(v.get("cold_requests") or 0 for v in ours) / max(sum(v.get("requests") or 0 for v in ours), 1)
        ref = dict(state["reference"])
        ref["requests"] = ref.get("requests") or traffic
        ref["cold_requests"] = round(cold_share * ref["requests"])
        for regime in (("trend" if trend else "rest"), "all"):
            total[regime].setdefault("reference", board.Sum()).add(ref)
            for v in ours:
                total[regime].setdefault(str(v["model_version"]).rsplit("_v", 1)[-1], board.Sum()).add(v)
    return total


def values(s: "board.Sum") -> tuple[dict, dict]:
    n, c = max(s.requests, 1), s.cold_requests
    value = {"all": s.buys / n, "cold": s.cold_buys / max(c, 1), "warm": (s.buys - s.cold_buys) / max(n - c, 1), "eur": s.revenue / n}
    return value, {"all": s.requests, "cold": c, "warm": s.requests - c}


def pooled(rows: dict, suffixes: tuple) -> tuple[dict, dict] | None:
    total = board.Sum()
    for s in suffixes:
        if s in rows:
            for field in ("requests", "cold_requests", "buys", "cold_buys", "revenue"):
                setattr(total, field, getattr(total, field) + getattr(rows[s], field))
    return values(total) if total.requests else None


def contrast_lines(rows: dict) -> list[str]:
    """The crossed questions on one regime's rows: the difference, its standard errors, the revenue per request."""
    out = []
    for title, with_it, without in CONTRASTS:
        a, b = pooled(rows, with_it), pooled(rows, without)
        if a and b:
            (va, na), (vb, nb) = a, b
            out.append(title + ": " + ", ".join(
                f"{k} {va[k] - vb[k]:+.3f} ({(va[k] - vb[k]) / (SPREAD[k] * (1 / max(na[k], 1) + 1 / max(nb[k], 1)) ** 0.5):+.1f} se)"
                for k in ("all", "cold", "warm")) + f"; EUR per request {va['eur']:.3f} against {vb['eur']:.3f}; {na['all']:,} against {nb['all']:,} requests")
    return out


def arms_table(since: int, end: int, suffixes: list[str]) -> list[str]:
    total = read(since, end)
    what = {s: w for s, w, _ in ARMS}
    lines = []
    for regime, title in (("all", "all minutes"), ("rest", "minutes without a trend"), ("trend", "minutes of a trend")):
        rows = total[regime]
        if "reference" not in rows or not any(s in rows for s in suffixes):
            lines += [f"**{title.capitalize()}**: nothing yet (a piece needs 15 minutes).", ""]
            continue
        ref, _ = values(rows["reference"])
        first = values(rows[suffixes[0]]) if suffixes[0] in rows else None
        lines += [f"**{title.capitalize()}** — reference {ref['all']:.3f} (cold {ref['cold']:.3f}, warm {ref['warm']:.3f})", "",
                  "| Arm | What it is | Requests | Overall | Over the reference | Cold | Warm | Against `v" + suffixes[0] + "`: overall, cold, warm (standard errors) |",
                  "|---|---|---|---|---|---|---|---|"]
        for s in suffixes:
            if s not in rows:
                continue
            v, n = values(rows[s])
            against = "" if first is None or s == suffixes[0] else ", ".join(
                f"{v[k] - first[0][k]:+.2f} ({(v[k] - first[0][k]) / (SPREAD[k] * (1 / max(n[k], 1) + 1 / max(first[1][k], 1)) ** 0.5):+.1f})"
                for k in ("all", "cold", "warm"))
            lines.append(f"| `v{s}` | {what.get(s, '')} | {n['all']:,} | {v['all']:.3f} | {v['all'] - ref['all']:+.3f} | {v['cold']:.3f} | {v['warm']:.3f} | {against} |")
        lines.append("")
        lines += [f"- Pooled, {c}." for c in contrast_lines(rows)] + [""]
    return lines


def gap_table(end: int) -> list[str]:
    lines = ["| Window | Place | Us | Next team | Gap | Gap on cold requests | Reference | Answered on time |", "|---|---|---|---|---|---|---|---|"]
    for minutes in (15, 30, 60, 180):
        req = urllib.request.Request(f"{URL}?from={end - 60 * minutes}&to={end}", headers={"User-Agent": "datathon-agent/experiments.py"})
        with urllib.request.urlopen(req, timeout=30) as r:
            state = json.loads(r.read())
        teams = {t["team_id"]: t for t in state["teams"]}
        us = teams.get(ME)
        if not us:
            continue
        others = sorted((t for k, t in teams.items() if k != ME), key=lambda t: -(t.get("conversion") or 0))
        cold = max(t.get("cold_conversion") or 0 for t in others)
        conv = us.get("conversion") or 0.0
        place = 1 + sum((t.get("conversion") or 0) > conv for t in others)
        lines.append(f"| {minutes} min | {place} | {conv:.3f} | {others[0]['team_id']} {others[0].get('conversion') or 0:.3f} | "
                     f"{conv - (others[0].get('conversion') or 0):+.3f} | {(us.get('cold_conversion') or 0) - cold:+.3f} | "
                     f"{state['reference'].get('conversion') or 0:.3f} | {us.get('on_time') or 0:.1f} % |")
    return lines


def main() -> None:
    now = int(time.time())
    end = now - now % 300
    req = urllib.request.Request(URL, headers={"User-Agent": "datathon-agent/experiments.py"})
    with urllib.request.urlopen(req, timeout=30) as r:
        state = json.loads(r.read())
    if state.get("mode") not in (None, "practice"):
        print(f"the board is hidden (mode {state.get('mode')}): experiments.md left as it is")
        return
    progress = state.get("progress") or {}
    score = sorted(((k, v[-1][1], v[-2][1] if len(v) > 1 else float("nan")) for k, v in progress.items() if v), key=lambda t: -t[1])[:5]
    common = max(epoch(s) for _, _, s in ARMS)
    earlier = sorted({epoch(s) for _, _, s in ARMS})
    block = [START, f"_Refreshed {hhmm(now, 1)} CET on {(datetime.fromtimestamp(now, timezone.utc) + timedelta(hours=1)).strftime('%d %b %Y')} "
                    f"(board to {hhmm(end, 1)} CET). Expected purchases per 100 requests, the organisers' own number._", "",
             "### The gap to the next team", ""] + gap_table(end) + ["",
             "Official hourly score, hour in progress (previous full hour): " + ", ".join(f"{k} {a:.1f} ({b:.1f})" for k, a, b in score) + ".", "",
             f"### The arms now serving, over the same minutes (since {hhmm(common, 1)} CET, when the last one started)", ""]
    block += arms_table(common, end, [s for s, _, _ in ARMS])
    if len(earlier) > 1 and earlier[-2] != common:
        older = [s for s, _, st in ARMS if epoch(st) <= earlier[-2]]
        block += [f"### The same for the arms that were already serving at {hhmm(earlier[-2], 1)} CET, since then", ""] + arms_table(earlier[-2], end, older)
    block += ["A difference counts from two standard errors and 0.15; a quarter of an hour of a small arm is a lottery.", END]
    path = HERE / "experiments.md"
    text = path.read_text(encoding="utf-8")
    head, rest = text.split(START, 1)
    tail = rest.split(END, 1)[1]
    path.write_text(head + "\n".join(block) + tail, encoding="utf-8", newline="")
    print("\n".join(block[1:]))


if __name__ == "__main__":
    main()
