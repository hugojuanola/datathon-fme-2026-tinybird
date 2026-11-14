#!/usr/bin/env python3
"""Keep the record of the best model we have served: writes best_model.md at the root of the repository.

    python realtime_analyisi_leaderboard/best_model.py

For every `model_version` we served it reads the organisers' own number — expected purchases per 100
requests under the hidden model (leaderboard API, `by=model`) — over the whole practice round, and then the
reference recommender over the SAME minutes that version was live. Versions are ranked by that margin, so a
version is not rewarded for having run during an easy hour. Stdlib only; read-only; no RawTree query.
"""
from __future__ import annotations

import json
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

PIECE = 3 * 3600      # the API serves windows of 15 minutes to 3 hours, in 5-minute steps
MIN_RANKED = 1500     # requests a version needs before it can hold the record
NOISE = 0.15          # differences below this are not differences (two identical arms differed by 0.12-0.67)

WHAT = {  # what each version is, in one line (details: docs/findings.md)
    "baseline": "all-time best sellers (the starter baseline)",
    "v4a": "rules: popularity × measured lifts (just-viewed ×3)", "v4b": "rules: popularity × measured lifts (just-viewed ×1.5)",
    "skore_money_v4": "rules: popularity × measured lifts",
    "skore_money_v5": "first learned ranker: P(click) × P(purchase | click) over the rules' candidates",
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
}


def fetch(start: int, end: int) -> dict:
    req = urllib.request.Request(f"{URL}?by=model&from={start}&to={end}", headers={"User-Agent": "datathon-agent/best_model.py"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


CACHE: dict[tuple[int, int], dict] = {}


def window(start: int, end: int, me: str) -> dict:
    """Requests-weighted totals between two 5-minute marks: every version of ours, and the reference."""
    out: dict = {"versions": {}, "ref": [0, 0.0, 0.0, 0.0]}   # ref: requests, buys, cold requests, cold buys
    for piece in range(start, end, PIECE):
        key = (piece, min(piece + PIECE, end))
        if key not in CACHE:
            CACHE[key] = fetch(*key)
            time.sleep(0.2)
        state = CACHE[key]
        ours = [v for t in state["teams"] if t["team_id"] == me for v in (t.get("versions") or [])]
        traffic = max((t.get("requests") or 0 for t in state["teams"]), default=0)
        share = sum(v.get("cold_requests") or 0 for v in ours) / max(sum(v.get("requests") or 0 for v in ours), 1)
        ref = state["reference"]
        n = ref.get("requests") or traffic
        out["ref"][0] += n
        out["ref"][1] += n * (ref.get("conversion") or 0.0)
        out["ref"][2] += share * n
        out["ref"][3] += share * n * (ref.get("cold_conversion") or 0.0)
        for v in ours:
            s = out["versions"].setdefault(str(v.get("model_version")), {"n": 0, "buys": 0.0, "cold_n": 0, "cold_buys": 0.0,
                                                                         "eur": 0.0, "first": float("inf"), "last": 0.0})
            req, cold = v.get("requests") or 0, v.get("cold_requests") or 0
            s["n"] += req
            s["buys"] += req * (v.get("conversion") or 0.0)
            s["cold_n"] += cold
            s["cold_buys"] += cold * (v.get("cold_conversion") or 0.0)
            s["eur"] += req * (v.get("revenue_per_request") or 0.0)
            s["first"], s["last"] = min(s["first"], v.get("first") or s["first"]), max(s["last"], v.get("last") or 0.0)
    return out


def rates(n: float, buys: float, cold_n: float, cold_buys: float) -> tuple[float, float, float]:
    conv = buys / max(n, 1)
    cold = cold_buys / cold_n if cold_n else float("nan")
    warm = (buys - cold_buys) / (n - cold_n) if n > cold_n else float("nan")
    return conv, cold, warm


def git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=20).stdout.strip()
    except Exception:
        return ""


def main() -> None:
    me = team_id()
    state = fetch(*(lambda e: (e - 3600, e))(int(time.time()) // 300 * 300))
    now_mark = int(state["window"][1]) // 300 * 300
    start = int(state.get("practice_start") or state["limits"]["earliest"])
    if state.get("mode") not in ("practice",):   # the board is hidden during the final: keep the last record
        print(f"mode {state.get('mode')}: best_model.md left as it is")
        return
    whole = window(start, now_mark, me)
    rows = []
    for name, s in whole["versions"].items():
        if s["n"] < 300 or not s["last"]:
            continue
        a = int(s["first"]) // 300 * 300
        b = min(-(-int(s["last"]) // 300) * 300, now_mark)
        if b - a < 900:
            a = b - 900
        w = window(a, b, me)
        v = w["versions"].get(name)
        if not v:
            continue
        conv, cold, warm = rates(v["n"], v["buys"], v["cold_n"], v["cold_buys"])
        rconv, rcold, rwarm = rates(*w["ref"])
        rows.append({"name": name, "n": v["n"], "conv": conv, "cold": cold, "warm": warm, "ref": rconv, "margin": conv - rconv,
                     "cold_margin": cold - rcold, "warm_margin": warm - rwarm, "eur": v["eur"] / max(v["n"], 1),
                     "from": datetime.fromtimestamp(a, timezone.utc), "to": datetime.fromtimestamp(b, timezone.utc),
                     "explore": "explore" in name})
    rows.sort(key=lambda r: -r["margin"])
    ranked = [r for r in rows if r["n"] >= MIN_RANKED and not r["explore"]]
    if not ranked:
        print("no version with enough requests yet")
        return
    best = ranked[0]
    tied = [r for r in ranked[1:] if best["margin"] - r["margin"] < NOISE]
    best_cold = max(ranked, key=lambda r: r["cold_margin"])
    best_warm = max(ranked, key=lambda r: r["warm_margin"])
    cet = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%d %b %Y, %H:%M")

    path = ROOT / "best_model.md"
    record = []
    if path.exists():
        old = path.read_text(encoding="utf-8")
        if "## Record" in old:
            record = [ln for ln in old.split("## Record", 1)[1].splitlines() if ln.startswith("- ")]
    leader = f"`{best['name']}`"
    if not record or leader not in record[-1]:
        record.append(f"- {cet} CET — {leader} takes the record: {best['conv']:.2f} expected purchases per 100 requests on "
                      f"{best['n']:,} requests, {best['margin']:+.2f} against the reference over the same minutes.")

    def row(r: dict) -> str:
        mark = " **← record**" if r is best else (" (tied)" if r in tied else "")
        return (f"| `{r['name']}`{mark} | {WHAT.get(r['name'], 'see docs/findings.md')} | {r['from']:%H:%M}–{r['to']:%H:%M} | {r['n']:,} | "
                f"{r['conv']:.2f} | {r['ref']:.2f} | **{r['margin']:+.2f}** | {r['cold']:.2f} ({r['cold_margin']:+.2f}) | "
                f"{r['warm']:.2f} ({r['warm_margin']:+.2f}) | {r['eur']:.2f} |")

    md = [
        "# Best model so far", "",
        f"_Updated {cet} CET by [`realtime_analyisi_leaderboard/best_model.py`](realtime_analyisi_leaderboard/best_model.py). "
        "Numbers are the organisers' own: expected purchases per 100 requests under the hidden model, per `model_version`._", "",
        f"**Record: `{best['name']}`** — {WHAT.get(best['name'], 'see docs/findings.md')}. "
        f"{best['conv']:.2f} expected purchases per 100 requests on {best['n']:,} requests, against {best['ref']:.2f} for the "
        f"organisers' reference over the same minutes: **{best['margin']:+.2f}**.", "",
        ("Tied with it, within what the measurement can tell apart (" + f"{NOISE}" + " points): "
         + ", ".join(f"`{r['name']}` ({r['margin']:+.2f})" for r in tied) + ".") if tied else "No other version is within the noise of it.", "",
        f"- **Best on cold requests** (new shopper, or a new product among the recent views — what the final is expected to bring): "
        f"`{best_cold['name']}`, {best_cold['cold']:.2f} against the reference's {best_cold['cold'] - best_cold['cold_margin']:.2f}.",
        f"- **Best on the other requests** (known shoppers): `{best_warm['name']}`, {best_warm['warm']:.2f} against "
        f"{best_warm['warm'] - best_warm['warm_margin']:.2f}.",
        f"- **Code**: branch `javier`, last commit on `reco/` or `offline/`: `{git('log', '-1', '--format=%h — %s', '--', 'reco', 'offline')}`. "
        "Model files: `models/`.", "",
        "## Every version we have served", "",
        "Ranked by the margin over the reference in the minutes each version was live (UTC). Exploration arms and versions "
        f"with fewer than {MIN_RANKED:,} requests are listed but cannot hold the record.", "",
        "| Version | What it is | Live (UTC) | Requests | Conversion | Reference, same minutes | Margin | Cold (margin) | Other requests (margin) | € per request |",
        "|---|---|---|---|---|---|---|---|---|---|",
        *[row(r) for r in rows], "",
        "## How to read it", "",
        "- The number is an expectation computed by the organisers from the hidden model, not a count of purchases, so it has no "
        "coin flip in it — but it still moves: on 14 Nov two arms running the same code differed by 0.12 over half an hour, and "
        "three identical arms read 1.92, 2.40 and 2.59 over a quarter of an hour. A version needs thousands of requests, and a "
        f"lead of less than about {NOISE} is a tie.",
        "- Each version is compared with the reference over its own minutes, because the store is easier in some hours than in others.",
        "- Versions whose only difference is the trend lift behave identically while no trend is running.", "",
        "## Record", "",
        *record, "",
    ]
    path.write_text("\n".join(md), encoding="utf-8")
    print(f"record: {best['name']} {best['conv']:.2f} vs reference {best['ref']:.2f} ({best['margin']:+.2f}) on {best['n']:,} requests; "
          f"tied: {', '.join(r['name'] for r in tied) or 'none'}; best cold {best_cold['name']}; best warm {best_warm['name']}")


if __name__ == "__main__":
    main()
