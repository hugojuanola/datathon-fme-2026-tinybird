#!/usr/bin/env python3
"""Keep the record of the best model we have served: writes best_model.md at the root of the repository.

    python realtime_analyisi_leaderboard/best_model.py

For every `model_version` we served it reads the organisers' own number — expected purchases per 100
requests under the hidden model (leaderboard API, `by=model`) — in half-hour pieces over the whole practice
round, and compares each version with the reference recommender over the SAME half hours, weighted by how
many requests the version had in each. So a version is not rewarded for having run during an easy hour.

Half-hour pieces on purpose: a longer window with many versions in it comes back without the small ones.
Finished pieces are cached in $SKORE_DATA_DIR, so a run costs one or two calls. Stdlib only; read-only.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "scripts"))
from leaderboard import URL, team_id  # noqa: E402
from rt import load_env  # noqa: E402

PIECE = 1800          # seconds; the API takes windows of 15 minutes to 3 hours in 5-minute steps
MIN_RANKED = 1500     # requests a version needs before it can hold the record
NOISE = 0.15          # differences below this are not differences (identical arms differed by 0.12-0.67)

WHAT = {  # what each version is, in one line (details: docs/findings.md)
    "baseline": "all-time best sellers (the starter baseline)",
    "v4a": "rules: popularity × measured lifts (just-viewed ×3)", "v4b": "rules: popularity × measured lifts (just-viewed ×1.5)",
    "skore_money_v4": "rules: popularity × measured lifts",
    "skore_money_v5": "first learned ranker: P(click) × P(purchase given a click) over the rules' candidates",
    "skore_money_v8c": "variant of v8 (see docs/findings.md)", "skore_money_v9d": "variant of v9 (see docs/findings.md)",
    "skore_money_v12": "variant served 16:29–16:53 UTC next to v11 (see docs/findings.md)",
    "skore_money_v6": "v5 + shopper × brand history, new-product and discount features",
    "skore_money_v7": "+ product attributes from the description (20 phrases, 2 per product)",
    "skore_money_v8": "v7 without the brand features, refit on all the data",
    "skore_money_v9": "attributes + carts by subcategory; learned from the old log and today's feedback",
    "skore_money_v9w": "v9 with today's feedback weighted ×20 (best on cold requests)",
    "skore_money_v11": "routed: v9w for cold requests, v9 for the rest",
    "skore_money_v13": "routed: v9w for cold requests, v10 for the rest",
    "skore_money_v14": "v11 + trend lift (no trend ran while it was live: same behaviour as v11)",
    "skore_money_v15": "v11 + weaker trend lift (no trend ran while it was live)",
    "skore_money_v21": "v9 everywhere, trend lift off", "skore_money_v22": "v9 everywhere, trend lift ^0.75",
    "skore_money_v23": "routed v9w cold / v9 warm, trend lift off", "skore_money_v24": "routed v9w cold / v9 warm, trend lift ^0.75",
    "skore_money_v25": "v16 everywhere (retrained on all of 14 Nov), trend lift off", "skore_money_v26": "v16 everywhere, trend lift ^0.75",
    "skore_money_v27": "routed v16w cold / v16 warm, trend lift off", "skore_money_v28": "routed v16w cold / v16 warm, trend lift ^0.75",
    "skore_money_v31": "v9 everywhere, trend lift at full strength (^1.0)",
    "skore_money_v32": "v9 × organic ^0.5 (a third model: what shoppers go on to buy in the store), trend lift ^1.0",
    "skore_money_v33": "v9b = v9's 52 features retrained on all of 14 Nov, trend lift ^1.0",
    "skore_money_v34": "v9 everywhere, no trend lift (control for the trends)",
    "skore_money_v35": "v9 everywhere, trend lift ^0.5 (dose)",
    "skore_money_v36": "v32 (v9 × organic, trend lift ^1.0) with products added during the event × 1.5 for known shoppers",
}
RANKER = {  # the ranker spec each version uses in `reco/serve.py` ("a|b" = a for cold requests, b for the rest)
    "skore_money_v5": "v5", "skore_money_v8": "v8", "skore_money_v9": "v9", "skore_money_v9w": "v9w",
    "skore_money_v11": "v9w|v9", "skore_money_v13": "v9w|v10", "skore_money_v14": "v9w|v9", "skore_money_v15": "v9w|v9",
    "skore_money_v21": "v9", "skore_money_v22": "v9", "skore_money_v23": "v9w|v9", "skore_money_v24": "v9w|v9",
    "skore_money_v25": "v16", "skore_money_v26": "v16", "skore_money_v27": "v16w|v16", "skore_money_v28": "v16w|v16",
}
TONIGHT = ("**Being measured against the record** (all on the v9 ranker, trend lift at full strength; live since 21:33 UTC on 14 Nov): "
           "`skore_money_v31` (30 %) v9 itself, `v32` (30 %) v9 × a third model of what shoppers go on to buy in the store, `v33` (20 %) "
           "v9's features retrained on all of Saturday, `v36` (20 %) `v32` with products added during the event × 1.5. `v31`, `v32` and "
           "`v33` have run since 20:35 UTC, until 21:33 next to `v34` (no trend lift) and `v35` (lift ^0.5). Read the night with "
           "`python scripts/arms.py 21:35 07:30 | python realtime_analyisi_leaderboard/pool_arms.py 'v9=31' 'v9 x organic=32' "
           "'organic, new x1.5=36' 'v9b=33'` on Sunday morning. Before them, 17:45–20:30 UTC, `v21`–`v28` compared v9, v9w cold + "
           "v9 warm, v16 and v16w cold + v16 warm, each with the trend lift off and at ^0.75: v9 everywhere led (+0.38 over the reference "
           "on 7,186 requests), v16 lost on warm requests (1.78 against 1.97, 2.7 standard errors) and the lift at ^0.75 changed nothing.")


def fetch(start: int, end: int) -> dict:
    req = urllib.request.Request(f"{URL}?by=model&from={start}&to={end}", headers={"User-Agent": "datathon-agent/best_model.py"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def piece(start: int, end: int, me: str, cache: dict, settled: bool) -> dict:
    """One half hour of the board, reduced to what we need: our versions, the reference, the traffic."""
    key = f"{start}-{end}"
    if key in cache:
        return cache[key]
    state = fetch(start, end)
    time.sleep(0.15)
    ours = [v for t in state["teams"] if t["team_id"] == me for v in (t.get("versions") or [])]
    out = {"traffic": max((t.get("requests") or 0 for t in state["teams"]), default=0),
           "ref": state["reference"].get("conversion") or 0.0, "ref_cold": state["reference"].get("cold_conversion") or 0.0,
           "versions": {str(v.get("model_version")): [v.get("requests") or 0, v.get("conversion") or 0.0, v.get("cold_requests") or 0,
                                                      v.get("cold_conversion") or 0.0, v.get("revenue_per_request") or 0.0]
                        for v in ours}}
    if settled:   # a half hour that ended a while ago does not change any more
        cache[key] = out
    return out


def git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=20).stdout.strip()
    except Exception:
        return ""


def main() -> None:
    load_env()
    me = team_id()
    mark = int(time.time()) // 300 * 300
    state = fetch(mark - 3600, mark)
    if state.get("mode") != "practice":   # the board is hidden during the final: keep the last record
        print(f"mode {state.get('mode')}: best_model.md left as it is")
        return
    start = int(state.get("practice_start") or state["limits"]["earliest"])
    cache_file = Path(os.environ.get("SKORE_DATA_DIR", ROOT / "data")) / "board_by_model_cache.json"
    cache = json.loads(cache_file.read_text(encoding="utf-8")) if cache_file.exists() else {}
    tot: dict[str, dict] = {}
    thin = 0
    for a in range(start, mark - 899, PIECE):   # a last piece shorter than 15 minutes cannot be asked for: it waits
        b = min(a + PIECE, mark)
        p = piece(a, b, me, cache, settled=b <= mark - 900)
        served = sum(v[0] for v in p["versions"].values())
        share = sum(v[2] for v in p["versions"].values()) / max(served, 1)   # share of cold requests in this half hour
        ref_warm = (p["ref"] - share * p["ref_cold"]) / (1 - share) if share < 1 else float("nan")
        if p["versions"] and served < 0.5 * p["traffic"]:
            thin += 1
        for name, (n, conv, cold_n, cold_conv, eur) in p["versions"].items():
            t = tot.setdefault(name, {"n": 0, "buys": 0.0, "cold_n": 0, "cold_buys": 0.0, "eur": 0.0, "ref": 0.0, "ref_cold": 0.0,
                                      "ref_warm": 0.0, "first": a, "last": b})
            warm_n = n - cold_n
            t["n"] += n
            t["buys"] += n * conv
            t["cold_n"] += cold_n
            t["cold_buys"] += cold_n * cold_conv
            t["eur"] += n * eur
            t["ref"] += n * p["ref"]                 # the reference, weighted like this version
            t["ref_cold"] += cold_n * p["ref_cold"]
            t["ref_warm"] += warm_n * (ref_warm if ref_warm == ref_warm else p["ref"])
            t["last"] = b
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(cache), encoding="utf-8")

    rows = []
    for name, t in tot.items():
        if t["n"] < 300:
            continue
        warm_n = t["n"] - t["cold_n"]
        conv, ref = t["buys"] / t["n"], t["ref"] / t["n"]
        cold = t["cold_buys"] / t["cold_n"] if t["cold_n"] else float("nan")
        warm = (t["buys"] - t["cold_buys"]) / warm_n if warm_n else float("nan")
        rows.append({"name": name, "n": t["n"], "conv": conv, "ref": ref, "margin": conv - ref, "cold": cold, "warm": warm,
                     "cold_margin": cold - t["ref_cold"] / t["cold_n"] if t["cold_n"] else float("nan"),
                     "warm_margin": warm - t["ref_warm"] / warm_n if warm_n else float("nan"), "eur": t["eur"] / t["n"],
                     "from": datetime.fromtimestamp(t["first"], timezone.utc), "to": datetime.fromtimestamp(t["last"], timezone.utc),
                     "explore": "explore" in name})
    rows.sort(key=lambda r: -r["margin"])
    ranked = [r for r in rows if r["n"] >= MIN_RANKED and not r["explore"]]
    if not ranked:
        print("no version with enough requests yet")
        return
    path = ROOT / "best_model.md"
    record = []
    if path.exists():
        old = path.read_text(encoding="utf-8")
        if "## Record" in old:
            record = [ln for ln in old.split("## Record", 1)[1].splitlines() if ln.startswith("- ")]
    best = ranked[0]
    # The record changes hands only on a lead the measurement can tell apart: the holder keeps it against a
    # challenger ahead by less than NOISE (a 6 % arm with two lucky quarter-hours is worth that much).
    holder = next((r for r in ranked if record and f"`{r['name']}` takes the record" in record[-1]), None)
    if holder is not None and best["margin"] - holder["margin"] < NOISE:
        best = holder
    tied = [r for r in ranked if r is not best and best["margin"] - r["margin"] < NOISE]
    best_cold = max(ranked, key=lambda r: r["cold_margin"])
    best_warm = max(ranked, key=lambda r: r["warm_margin"])
    cet = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%d %b %Y, %H:%M")
    leader = f"`{best['name']}`"
    if not record or leader not in record[-1]:
        record.append(f"- {cet} CET — {leader} takes the record: {best['conv']:.2f} expected purchases per 100 requests on "
                      f"{best['n']:,} requests, {best['margin']:+.2f} against the reference over the same half hours.")

    def row(r: dict) -> str:
        mark_ = " **← record**" if r is best else (" (tied)" if r in tied else "")
        return (f"| `{r['name']}`{mark_} | {WHAT.get(r['name'], 'see docs/findings.md')} | {r['from']:%H:%M}–{r['to']:%H:%M} | {r['n']:,} | "
                f"{r['conv']:.2f} | {r['ref']:.2f} | **{r['margin']:+.2f}** | {r['cold']:.2f} ({r['cold_margin']:+.2f}) | "
                f"{r['warm']:.2f} ({r['warm_margin']:+.2f}) | {r['eur']:.2f} |")

    md = [
        "# Best model so far", "",
        f"_Updated {cet} CET by [`realtime_analyisi_leaderboard/best_model.py`](realtime_analyisi_leaderboard/best_model.py). "
        "Numbers are the organisers' own: expected purchases per 100 requests under the hidden model, per `model_version`._", "",
        f"**Record: `{best['name']}`** — {WHAT.get(best['name'], 'see docs/findings.md')}. "
        f"{best['conv']:.2f} expected purchases per 100 requests on {best['n']:,} requests, against {best['ref']:.2f} for the "
        f"organisers' reference over the same half hours: **{best['margin']:+.2f}**.", "",
        ("Tied with it, within what the measurement can tell apart (" + f"{NOISE}" + " points): "
         + ", ".join(f"`{r['name']}` ({r['margin']:+.2f})" for r in tied) + ".") if tied else "No other version is within the noise of it.", "",
        f"- **Best on cold requests** (new shopper, or a new product among the recent views — what the final is expected to bring): "
        f"`{best_cold['name']}`, {best_cold['cold']:.2f} against the reference's {best_cold['cold'] - best_cold['cold_margin']:.2f}.",
        f"- **Best on the other requests** (known shoppers): `{best_warm['name']}`, {best_warm['warm']:.2f} against "
        f"{best_warm['warm'] - best_warm['warm_margin']:.2f}. On cold requests every version of ours since v7 is 1.0 to 1.5 above the "
        "reference; on the other requests the best of ours are level with it. That is the gap still open.",
        f"- **Code**: branch `javier`, last commit on `reco/` or `offline/`: `{git('log', '-1', '--format=%h — %s', '--', 'reco', 'offline')}`. "
        "Model files: `models/`.", "",
        TONIGHT, "",
        "## Putting the record back", "",
        f"To serve the record alone: in `reco/serve.py` set `ARMS = ((\"{best['name']}\", \"model\", "
        f"\"{RANKER.get(best['name'], '<its ranker>')}\", {{}}, 100),)`, commit, then run "
        "`powershell -ExecutionPolicy Bypass -File scripts\\swap_server.ps1`. The script starts the new server in standby as a "
        "process of its own, waits for its self-test (every arm must answer real requests with valid lists) and only then stops "
        "the old one; if the new one is not fit, nothing changes. Never start or stop a server any other way.", "",
        "## Every version we have served", "",
        "Ranked by the margin over the reference in the half hours each version was live (UTC), the reference weighted by the "
        f"version's own requests. Exploration arms and versions with fewer than {MIN_RANKED:,} requests are listed but cannot "
        "hold the record.", "",
        "| Version | What it is | Live (UTC) | Requests | Conversion | Reference, same half hours | Margin | Cold (margin) | Other requests (margin) | € per request |",
        "|---|---|---|---|---|---|---|---|---|---|",
        *[row(r) for r in rows], "",
        "## How to read it", "",
        "- The number is an expectation computed by the organisers from the hidden model, not a count of purchases, so it has no "
        "coin flip in it — but it still moves: on 14 Nov two arms running the same code differed by 0.12 over half an hour, and "
        "three identical arms read 1.92, 2.40 and 2.59 over a quarter of an hour. A version needs thousands of requests, and a "
        f"lead of less than about {NOISE} is a tie.",
        "- Each version is compared with the reference over its own half hours, because the store is easier in some hours than in others.",
        "- Versions whose only difference is the trend lift behave identically while no trend is running.", "",
        "## Record", "",
        *record, "",
    ]
    path.write_text("\n".join(md), encoding="utf-8")
    print(f"record: {best['name']} {best['conv']:.2f} vs reference {best['ref']:.2f} ({best['margin']:+.2f}) on {best['n']:,} requests; "
          f"tied: {', '.join(r['name'] for r in tied) or 'none'}; best cold {best_cold['name']}; best warm {best_warm['name']}; "
          f"{len(rows)} versions listed; half hours where our versions cover under half the traffic: {thin}")


if __name__ == "__main__":
    main()
