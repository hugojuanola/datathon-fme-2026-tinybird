#!/usr/bin/env python3
"""A trend on the organisers' metric and in the store: our arms inside it, every team before and inside it, its size.

    python realtime_analyisi_leaderboard/trend_board.py --since "2026-11-15 01:30" --until "2026-11-15 02:15" --sub "Leashes"   # UTC

The read of a trend has two halves. trend_read.py reads our own carousel: what each arm showed and what it
got for it. This one reads the rest, in three blocks:

1. our arms over the window on the organisers' metric (expected purchases per 100 requests, cold, warm,
   EUR per request) and the questions the arms are crossed on (ARMS and CONTRASTS of experiments.py);
2. the first eight teams over the window and over the same number of minutes before it: who rose with the
   trend, and our gap to the next team inside it against before it;
3. with --sub, the subcategory in the store (`shop.events`) per 5 minutes from half an hour before the
   window, next to its share of the views and purchases over the twelve hours before that: the size of the
   trend. A trend is compared with the day's share, never with the half hour before it; and the line the
   server logs when it finds a trend shows the lift at that moment, which is not the size.

Read-only and light: the public leaderboard API and one aggregate on the stream (0.2 s). Stdlib only.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
sys.path.insert(0, str(HERE))
import experiments as ex  # noqa: E402
from rt import load_env, query  # noqa: E402

USUAL_HOURS = 12       # the subcategory's usual share is measured on these hours, ending half an hour before the window
STORE = """
WITH sub AS (SELECT product_id::String AS pid FROM shop.catalog WHERE subcategory::String = '{sub}'
             UNION DISTINCT
             SELECT product_id::String AS pid FROM shop.catalog_updates
             WHERE change::String = 'new_product' AND subcategory::String = '{sub}')
SELECT if(t < '{near}', 'usual', formatDateTime(toStartOfFiveMinutes(t), '%Y-%m-%d %H:%i')) AS period,
       countIf(e = 'view') AS views, countIf(e = 'purchase') AS purchases,
       countIf(e = 'view' AND pid IN (SELECT pid FROM sub)) AS sub_views,
       countIf(e = 'add_to_cart' AND pid IN (SELECT pid FROM sub)) AS sub_carts,
       countIf(e = 'purchase' AND pid IN (SELECT pid FROM sub)) AS sub_purchases
FROM (SELECT ts::DateTime64(3) AS t, event_type::String AS e, product_id::String AS pid FROM shop.events
      WHERE ts >= '{far}' AND ts < '{end}')
GROUP BY period ORDER BY period"""


def arg(name: str, default: str | None = None) -> str | None:
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def stamp(ts: int) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def teams(start: int, end: int) -> tuple[dict, float]:
    """{team: its row on the board} and the reference's conversion, over [start, end)."""
    req = urllib.request.Request(f"{ex.URL}?from={start}&to={end}", headers={"User-Agent": "datathon-agent/trend_board.py"})
    with urllib.request.urlopen(req, timeout=30) as r:
        state = json.loads(r.read())
    return {t["team_id"]: t for t in state["teams"]}, state["reference"].get("conversion") or 0.0


def conv(team: dict | None) -> float:
    return (team or {}).get("conversion") or 0.0


def cold(team: dict | None) -> float:
    return (team or {}).get("cold_conversion") or 0.0


def gap(board: dict, value) -> float:
    """Ours minus the best of the others."""
    return value(board.get(ex.ME)) - max((value(t) for k, t in board.items() if k != ex.ME), default=0.0)


def main() -> None:
    if not arg("--since") or not arg("--until"):
        sys.exit('usage: trend_board.py --since "YYYY-MM-DD HH:MM" --until "YYYY-MM-DD HH:MM" [--sub "Subcategory"]   (UTC)')
    since, until, sub = ex.epoch(arg("--since")), ex.epoch(arg("--until")), arg("--sub")
    minutes = (until - since) // 60
    print(f"== {ex.hhmm(since)}-{ex.hhmm(until)} UTC ({ex.hhmm(since, 1)}-{ex.hhmm(until, 1)} CET), {minutes} minutes")

    print("\n1) OUR ARMS over the window — expected purchases per 100 requests")
    rows = ex.read(since, until)["all"]
    if "reference" in rows:
        ref, _ = ex.values(rows["reference"])
        print(f"   reference {ref['all']:.3f} / cold {ref['cold']:.3f} / warm {ref['warm']:.3f}")
        for s, _, _ in ex.ARMS:
            if s in rows:
                v, n = ex.values(rows[s])
                print(f"   v{s}  requests {n['all']:>6,}  overall {v['all']:.3f} ({v['all'] - ref['all']:+.3f})  cold {v['cold']:.3f}  "
                      f"warm {v['warm']:.3f}  eur {v['eur']:.2f}")
        for line in ex.contrast_lines(rows):
            print(f"   > {line}")

    print(f"\n2) THE TEAMS over the {minutes} minutes before and over the window")
    before, ref_before = teams(since - (until - since), since)
    inside, ref_inside = teams(since, until)
    order = sorted(inside, key=lambda k: -conv(inside[k]))
    shown = order[:8] + ([ex.ME] if ex.ME in inside and ex.ME not in order[:8] else [])
    print(f"   {'':<10} {'before':>7} {'inside':>7} {'rise':>7} | {'cold before':>11} {'cold inside':>11} | on time")
    print(f"   {'reference':<10} {ref_before:7.3f} {ref_inside:7.3f} {ref_inside - ref_before:+7.3f} |")
    for k in shown:
        b, i = before.get(k), inside[k]
        was = f"{conv(b):7.3f} {conv(i):7.3f} {conv(i) - conv(b):+7.3f} | {cold(b):11.3f}" if b else f"{'-':>7} {conv(i):7.3f} {'-':>7} | {'-':>11}"
        print(f"   {k:<10} {was} {cold(i):11.3f} | {i.get('on_time') or 0:5.1f}%")
    if ex.ME in inside:
        n = inside[ex.ME].get("requests") or 180 * minutes       # three requests a second
        print(f"   our gap to the next team: inside {gap(inside, conv):+.3f} (cold {gap(inside, cold):+.3f}); before {gap(before, conv):+.3f} "
              f"(cold {gap(before, cold):+.3f}). Two teams over {minutes} minutes differ by about {ex.SPREAD['all'] * (2 / n) ** 0.5:.2f} by chance.")

    if sub:
        load_env()
        near = since - 1800
        data = query(STORE.format(sub=sub.replace("'", "\\'"), near=stamp(near), far=stamp(near - USUAL_HOURS * 3600), end=stamp(until + 900)))["data"]
        counts = {r["period"]: {k: float(v) for k, v in r.items() if k != "period"} for r in data}
        usual = counts.pop("usual", None)
        print(f"\n3) THE STORE: {sub} per 5 minutes (UTC; * = inside the window), against its share over the {USUAL_HOURS} hours to {ex.hhmm(near)}")
        if not usual or not usual["views"] or not usual["purchases"]:
            print("   no events in the hours before: nothing to compare with")
            return
        share_views, share_buys = usual["sub_views"] / usual["views"], usual["sub_purchases"] / usual["purchases"]
        print(f"   usual share: {100 * share_views:.2f} % of the views, {100 * share_buys:.2f} % of the purchases "
              f"({int(usual['sub_purchases']):,} of {int(usual['purchases']):,})")
        print(f"   {'':<7} {'views':>6} {'carts':>6} {'bought':>6} | {'% views':>8} {'x usual':>8} | {'% bought':>8} {'x usual':>8}")
        total = dict.fromkeys(("views", "purchases", "sub_views", "sub_purchases"), 0.0)
        for period in sorted(counts):
            r = counts[period]
            is_inside = since <= ex.epoch(period) < until
            pv, pb = r["sub_views"] / max(r["views"], 1), r["sub_purchases"] / max(r["purchases"], 1)
            print(f"   {period[11:]:<5} {'*' if is_inside else ' '} {int(r['sub_views']):>6} {int(r['sub_carts']):>6} {int(r['sub_purchases']):>6} | "
                  f"{100 * pv:8.2f} {pv / share_views:8.1f} | {100 * pb:8.2f} {pb / share_buys:8.1f}")
            if is_inside:
                for k in total:
                    total[k] += r[k]
        if total["views"] and total["purchases"]:
            pv, pb = total["sub_views"] / total["views"], total["sub_purchases"] / total["purchases"]
            print(f"   inside the window: {100 * pv:.2f} % of the views (x{pv / share_views:.1f}), {100 * pb:.2f} % of the purchases (x{pb / share_buys:.1f})")


if __name__ == "__main__":
    main()
