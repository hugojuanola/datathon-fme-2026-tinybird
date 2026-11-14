#!/usr/bin/env python3
"""One watch tick: where we stand on the leaderboard and how the live model is doing, by kind of shopper.

    python realtime_analyisi_leaderboard/tick.py            # last 30 minutes of our feedback
    python realtime_analyisi_leaderboard/tick.py --window 60
    python realtime_analyisi_leaderboard/tick.py --since "2026-11-14 13:34:00"   # UTC

Read-only (leaderboard API + SELECTs on the live tables only). Appends one row to history.csv and rewrites
latest.md, both next to this script. The interpretation of the numbers lives in README.md and notes/.

It is deliberately light on RawTree and on this laptop, which also serves live: the three queries only read
the last minutes of the live tables, and the shoppers' 60-day purchase history comes from the local cache
written by avanced_data_analysis/eda_pull.py ($SKORE_DATA_DIR/eda), not from a scan of shop.history_events.
"""
from __future__ import annotations

import csv
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "scripts"))
from leaderboard import URL, team_id  # noqa: E402
from rt import load_env, query  # noqa: E402

FEEDBACK = """(SELECT request_id::String AS rid, shown::Array(String) AS shown, clicked::String AS clicked,
       purchased::String AS purchased, revenue_eur::Float64 AS rev, served_by::String AS sb,
       fallback_reason::String AS reason, latency_ms
FROM {team}.feedback WHERE request_id != '__init__' AND ts > {start})"""
REQUESTS = """(SELECT request_id::String AS rid, user_id::String AS u, is_new_user::Bool AS is_new
FROM shop.requests WHERE ts > {start} - INTERVAL 2 MINUTE)"""
VERSIONS = "(SELECT request_id::String AS rid, any(model_version::String) AS mv FROM {team}.submissions GROUP BY rid)"

HEALTH = """
SELECT sb AS served_by, reason, count() AS requests, round(quantile(0.95)(latency_ms::Float64)) AS p95_ms
FROM {fb} GROUP BY served_by, reason ORDER BY requests DESC"""

# conversion of what we served, per model version and per kind of shopper
SEGMENTS = """
SELECT s.mv AS model_version, if(r.is_new, 'new', 'known') AS shopper, count() AS requests,
       countIf(f.clicked != '') AS clicks, countIf(f.purchased != '') AS buys, round(sum(f.rev), 2) AS revenue
FROM {fb} AS f INNER JOIN {rq} AS r ON r.rid = f.rid INNER JOIN {vs} AS s ON s.rid = f.rid
WHERE f.sb = 'team'
GROUP BY model_version, shopper ORDER BY model_version, shopper"""

# what we showed known shoppers, one row per request; the purchase-history join is done locally
SHOWN = """
SELECT s.mv AS model_version, r.u AS u, f.shown AS shown, f.clicked AS clicked, f.purchased AS purchased
FROM {fb} AS f INNER JOIN {rq} AS r ON r.rid = f.rid INNER JOIN {vs} AS s ON s.rid = f.rid
WHERE f.sb = 'team' AND NOT r.is_new"""
NEW_PRODUCTS = """
SELECT DISTINCT product_id::String AS product_id, subcategory::String AS subcategory
FROM shop.catalog_updates WHERE change = 'new_product'"""

COLUMNS = ["utc", "mode", "rank", "conv", "cold", "on_time", "eur_req", "model", "best_rival", "rival_conv", "ref_conv",
           "ref_cold", "base_conv", "base_cold", "pct_of_way_to_ref", "window", "served_by_team_pct", "p95_ms",
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


def lever(shown: list[dict]) -> list[dict]:
    """The known-shopper lever (notes/2026-11-14_1406): of the products we showed a known shopper and that
    they had not bought, how many were in a subcategory where they have bought before, and how did each
    group sell? Per model version and overall."""
    try:
        import pandas as pd

        cache = Path(os.environ.get("SKORE_DATA_DIR", ROOT / "data")) / "eda"
        pur = pd.read_parquet(cache / "purchases.parquet", columns=["user_id", "product_id"])
        cat = pd.read_parquet(cache / "catalog.parquet", columns=["product_id", "subcategory"])
    except Exception as e:  # no pandas or no cache: the rest of the tick still works
        print(f"lever skipped: {e}", file=sys.stderr)
        return []
    if not shown:
        return []
    cat = pd.concat([cat, pd.DataFrame(query(NEW_PRODUCTS)["data"])], ignore_index=True).drop_duplicates("product_id")
    sub = cat.set_index("product_id").subcategory
    imp = pd.DataFrame(shown).explode("shown").rename(columns={"shown": "item"})
    pur = pur[pur.user_id.isin(imp.u.unique())]
    bought = set(zip(pur.user_id, pur.product_id))
    bought_sub = set(zip(pur.user_id, pur.product_id.map(sub)))
    imp = imp[[(u, i) not in bought for u, i in zip(imp.u, imp.item)]]
    imp["in_hist"] = [(u, s) in bought_sub for u, s in zip(imp.u, imp.item.map(sub))]
    imp["click"], imp["buy"] = imp.item == imp.clicked, imp.item == imp.purchased
    rows = []
    for name, g in [("all", imp)] + sorted(imp.groupby("model_version")):
        for flag, label in [(True, "bought in this subcategory before"), (False, "no purchase in this subcategory")]:
            d = g[g["in_hist"] == flag]
            rows.append({"model_version": name, "subcategory_history": label, "impressions": len(d),
                         "share_pct": pct(len(d), len(g)), "clicks": int(d.click.sum()), "buys": int(d.buy.sum()),
                         "buy_pct": pct(d.buy.sum(), len(d))})
    return rows


def main() -> None:
    load_env()
    team = team_id()
    if "--since" in sys.argv:
        since = sys.argv[sys.argv.index("--since") + 1]
        start, label = f"'{since}'", f"since {since} UTC"
    else:
        w = int(sys.argv[sys.argv.index("--window") + 1]) if "--window" in sys.argv else 30
        start, label = f"now() - INTERVAL {w} MINUTE", f"last {w} min"
    fb, rq, vs = FEEDBACK.format(team=team, start=start), REQUESTS.format(start=start), VERSIONS.format(team=team)
    row: dict = {"utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"), "window": label}

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

    seg = query(SEGMENTS.format(fb=fb, rq=rq, vs=vs))["data"]
    for s in seg:
        s["ctr_pct"], s["conv_pct"] = pct(int(s["clicks"]), int(s["requests"])), pct(int(s["buys"]), int(s["requests"]))
    for kind in ("new", "known"):
        n = sum(int(s["requests"]) for s in seg if s["shopper"] == kind)
        b = sum(int(s["buys"]) for s in seg if s["shopper"] == kind)
        row[f"{kind}_requests"], row[f"{kind}_conv_pct"] = n, pct(b, n)

    lev = lever(query(SHOWN.format(fb=fb, rq=rq, vs=vs))["data"])
    yes = next((x for x in lev if x["model_version"] == "all" and x["subcategory_history"].startswith("bought")), None)
    no = next((x for x in lev if x["model_version"] == "all" and x["subcategory_history"].startswith("no ")), None)
    row.update(lever_impr_share_pct=yes["share_pct"] if yes else "", lever_buy_pct=yes["buy_pct"] if yes else "",
               no_lever_buy_pct=no["buy_pct"] if no else "")

    hist = HERE / "history.csv"
    new_file = not hist.exists()
    with hist.open("a", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=COLUMNS)
        if new_file:
            wr.writeheader()
        wr.writerow({c: row.get(c, "") for c in COLUMNS})

    md = [f"# Latest tick — {row['utc']} UTC (our feedback: {label})\n",
          "Generated by `tick.py`; do not edit. Interpretation: [README.md](README.md).\n",
          "## Leaderboard (top 5 by conversion, reference, baseline)\n", table(board),
          "## Who served our shoppers\n", table(health),
          "## What we served: conversion by model version and kind of shopper\n", table(seg),
          "## Known shoppers, products never bought: subcategory purchase history, per model version\n", table(lev)]
    (HERE / "latest.md").write_text("\n".join(md), encoding="utf-8")
    print(json.dumps(row, ensure_ascii=False))
    print("\n".join(md[2:]))


if __name__ == "__main__":
    main()
