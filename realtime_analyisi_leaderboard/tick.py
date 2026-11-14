#!/usr/bin/env python3
"""One watch tick: where we stand on the leaderboard and how the live model is doing, by kind of shopper.

    python realtime_analyisi_leaderboard/tick.py            # last 30 minutes of our feedback
    python realtime_analyisi_leaderboard/tick.py --window 60

Read-only (leaderboard API + SELECTs). Appends one row to history.csv and rewrites latest.md, both next to
this script. Stdlib only. The interpretation of the numbers lives in README.md and notes/.
"""
from __future__ import annotations

import csv
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
from leaderboard import URL, team_id  # noqa: E402
from rt import load_env, query  # noqa: E402

FEEDBACK = """(SELECT request_id::String AS rid, shown::Array(String) AS shown, clicked::String AS clicked,
       purchased::String AS purchased, revenue_eur::Float64 AS rev, served_by::String AS sb,
       fallback_reason::String AS reason, latency_ms
FROM {team}.feedback WHERE request_id != '__init__' AND ts > now() - INTERVAL {w} MINUTE)"""
REQUESTS = """(SELECT request_id::String AS rid, user_id::String AS u, is_new_user::Bool AS is_new
FROM shop.requests WHERE ts > now() - INTERVAL {w} + 2 MINUTE)"""

HEALTH = """
SELECT sb AS served_by, reason, count() AS requests, round(quantile(0.95)(latency_ms::Float64)) AS p95_ms
FROM {fb} GROUP BY served_by, reason ORDER BY requests DESC"""

# conversion of what we served, per model version and per kind of shopper
SEGMENTS = """
SELECT s.mv AS model_version, if(r.is_new, 'new', 'known') AS shopper, count() AS requests,
       countIf(f.clicked != '') AS clicks, countIf(f.purchased != '') AS buys, round(sum(f.rev), 2) AS revenue
FROM {fb} AS f
INNER JOIN {rq} AS r ON r.rid = f.rid
INNER JOIN (SELECT request_id::String AS rid, any(model_version::String) AS mv FROM {team}.submissions GROUP BY rid) AS s
        ON s.rid = f.rid
WHERE f.sb = 'team'
GROUP BY model_version, shopper ORDER BY model_version, shopper"""

# the known-shopper lever (notes/2026-11-14_1406): products the shopper has never bought, split by whether
# the shopper has bought in that product's subcategory before. Are we showing them, and do they sell?
LEVER = """
SELECT if(hs.p > 0, 'bought in this subcategory before', 'no purchase in this subcategory') AS subcategory_history,
       count() AS impressions, countIf(x.clicked = x.item) AS clicks, countIf(x.purchased = x.item) AS buys
FROM (SELECT r.u AS u, arrayJoin(f.shown) AS item, f.clicked AS clicked, f.purchased AS purchased
      FROM {fb} AS f INNER JOIN {rq} AS r ON r.rid = f.rid WHERE f.sb = 'team' AND NOT r.is_new) AS x
INNER JOIN (SELECT product_id::String AS pid, any(subcategory::String) AS s
            FROM (SELECT product_id, subcategory FROM shop.catalog
                  UNION ALL SELECT product_id, subcategory FROM shop.catalog_updates WHERE change = 'new_product')
            GROUP BY pid) AS c ON c.pid = x.item
LEFT JOIN (SELECT e.user_id::String AS u, k.subcategory::String AS s, countIf(e.event_type = 'purchase') AS p
           FROM shop.history_events AS e INNER JOIN shop.catalog AS k ON k.product_id::String = e.product_id::String
           WHERE e.user_id::String IN (SELECT u FROM {rq}) GROUP BY u, s) AS hs ON hs.u = x.u AND hs.s = c.s
LEFT JOIN (SELECT DISTINCT user_id::String AS u, product_id::String AS pid, 1 AS b
           FROM shop.history_events WHERE event_type = 'purchase') AS hb ON hb.u = x.u AND hb.pid = x.item
WHERE hb.b = 0
GROUP BY subcategory_history ORDER BY subcategory_history"""

COLUMNS = ["utc", "mode", "rank", "conv", "cold", "on_time", "eur_req", "model", "best_rival", "rival_conv", "ref_conv",
           "ref_cold", "base_conv", "base_cold", "pct_of_way_to_ref", "window_min", "served_by_team_pct", "p95_ms",
           "new_requests", "new_conv_pct", "known_requests", "known_conv_pct", "lever_impr_share_pct",
           "lever_buy_pct", "no_lever_buy_pct"]


def pct(a: float, b: float) -> float | str:
    return round(100 * a / b, 3) if b else ""


def table(rows: list[dict]) -> str:
    if not rows:
        return "_no rows_\n"
    cols = list(rows[0])
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    out += ["| " + " | ".join(str(r[c]) for c in cols) + " |" for r in rows]
    return "\n".join(out) + "\n"


def main() -> None:
    w = int(sys.argv[sys.argv.index("--window") + 1]) if "--window" in sys.argv else 30
    load_env()
    team = team_id()
    fb, rq = FEEDBACK.format(team=team, w=w), REQUESTS.format(w=w)
    row: dict = {"utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"), "window_min": w}

    req = urllib.request.Request(URL, headers={"User-Agent": "datathon-agent/tick.py"})
    with urllib.request.urlopen(req, timeout=20) as r:
        state = json.loads(r.read())
    row["mode"] = state["mode"]
    teams = state.get("teams") or []
    me = next((t for t in teams if t["team_id"] == team), None)
    board = []
    if me:  # hidden during the final: only the live part below is available then
        rivals = [t for t in teams if t["team_id"] != team]
        best = max(rivals, key=lambda t: t["conversion"])
        ref, base = state["reference"], state["baseline"]
        row.update(rank=teams.index(me) + 1, conv=round(me["conversion"], 4), cold=round(me["cold_conversion"], 4),
                   on_time=round(me["on_time"], 1), eur_req=round(me["revenue_per_request"], 3),
                   model=me.get("model_version", ""), best_rival=best["team_id"], rival_conv=round(best["conversion"], 4),
                   ref_conv=round(ref["conversion"], 4), ref_cold=round(ref["cold_conversion"], 4),
                   base_conv=round(base["conversion"], 4), base_cold=round(base["cold_conversion"], 4),
                   pct_of_way_to_ref=pct(me["conversion"] - base["conversion"], ref["conversion"] - base["conversion"]))
        top = sorted(teams, key=lambda t: -t["conversion"])[:5]
        board = [{"team": t["team_id"] + (" (us)" if t is me else ""), "conv": round(t["conversion"], 3),
                  "cold": round(t["cold_conversion"], 3), "on_time": round(t["on_time"], 1),
                  "eur_req": round(t["revenue_per_request"], 3), "model": t.get("model_version", "")}
                 for t in top + [dict(ref, team_id="reference"), dict(base, team_id="baseline")]]

    health = query(HEALTH.format(fb=fb))["data"]
    total = sum(int(h["requests"]) for h in health)
    ours = next((h for h in health if h["served_by"] == "team"), None)
    row.update(served_by_team_pct=pct(int(ours["requests"]) if ours else 0, total), p95_ms=ours["p95_ms"] if ours else "")

    seg = query(SEGMENTS.format(fb=fb, rq=rq, team=team))["data"]
    for s in seg:
        s["ctr_pct"], s["conv_pct"] = pct(int(s["clicks"]), int(s["requests"])), pct(int(s["buys"]), int(s["requests"]))
    for kind in ("new", "known"):
        n = sum(int(s["requests"]) for s in seg if s["shopper"] == kind)
        b = sum(int(s["buys"]) for s in seg if s["shopper"] == kind)
        row[f"{kind}_requests"], row[f"{kind}_conv_pct"] = n, pct(b, n)

    lever = query(LEVER.format(fb=fb, rq=rq))["data"]
    for lv in lever:
        lv["buy_pct"] = pct(int(lv["buys"]), int(lv["impressions"]))
    imp = sum(int(lv["impressions"]) for lv in lever)
    yes = next((lv for lv in lever if lv["subcategory_history"].startswith("bought")), None)
    no = next((lv for lv in lever if lv["subcategory_history"].startswith("no ")), None)
    row.update(lever_impr_share_pct=pct(int(yes["impressions"]) if yes else 0, imp),
               lever_buy_pct=yes["buy_pct"] if yes else "", no_lever_buy_pct=no["buy_pct"] if no else "")

    hist = HERE / "history.csv"
    new_file = not hist.exists()
    with hist.open("a", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=COLUMNS)
        if new_file:
            wr.writeheader()
        wr.writerow({c: row.get(c, "") for c in COLUMNS})

    md = [f"# Latest tick — {row['utc']} UTC (window: last {w} min of our feedback)\n",
          "Generated by `tick.py`; do not edit. Interpretation: [README.md](README.md).\n",
          "## Leaderboard (top 5 by conversion, reference, baseline)\n", table(board),
          "## Who served our shoppers\n", table(health),
          "## What we served: conversion by model version and kind of shopper\n", table(seg),
          "## Known shoppers, products never bought: subcategory purchase history\n", table(lever)]
    (HERE / "latest.md").write_text("\n".join(md), encoding="utf-8")
    print(json.dumps(row, ensure_ascii=False))
    print("\n".join(md[2:]))


if __name__ == "__main__":
    main()
