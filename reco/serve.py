"""The live loop: pull new requests → rank → push answers. This process *is* our submission.

    python -m reco.serve            # answer live traffic (only ONE instance may run at a time)
    python -m reco.serve --dry      # same, but print instead of inserting: safe for testing

Design goals, in order: never die, never send an invalid answer, answer in ~1 s, be explainable.
"""
from __future__ import annotations

import json
import queue
import sys
import threading
import time
from pathlib import Path

from reco.rawtree import ROOT, insert, query
from reco.recommend import arm_of, is_valid, recommend, safe_list
from reco.state import State

VERSION = "v4"          # shown on the public leaderboard: keep it opaque
POLL_EVERY = 0.25       # seconds between polls of shop.requests
MAX_AGE_MS = 2800       # an answer must land within 3000 ms of the request ts: do not bother after this

NEW_REQUESTS = """
SELECT request_id::String AS id, toUnixTimestamp64Milli(ts::DateTime64(3)) AS ts_ms, user_id::String AS user,
       arrayMap(v -> v.product_id::String, recent_views::Array(JSON)) AS rv,
       toUnixTimestamp64Milli(now64(3)) AS now_ms
FROM shop.requests
WHERE ts > now64(3) - INTERVAL 4 SECOND
ORDER BY ts"""


def answer(state: State, req: dict) -> tuple[dict, dict]:
    """One submission row and one log row for a request. Never raises, never returns an invalid list."""
    arm = arm_of(req["id"])
    try:
        items, tiers = recommend(state, req["user"], req["rv"], arm)
        if not is_valid(state, items):
            raise ValueError(f"invalid list {items}")
    except Exception as e:
        print(f"recommend failed for {req['id']}: {str(e)[:200]}", flush=True)
        items, tiers, arm = safe_list(state), ["safe"] * 10, "safe"
    version = f"{VERSION}{arm[0]}"
    return ({"request_id": req["id"], "items": items, "model_version": version},
            {"kind": "served", "request_id": req["id"], "ts_ms": req["ts_ms"], "user_id": req["user"],
             "model_version": version, "arm": arm, "items": items, "tiers": tiers})


def log_writer(q: queue.Queue, dry: bool) -> None:
    """Off the hot path: keep what we served (and why) in a local file and in team_NN.scratch."""
    path = ROOT / "logs"
    path.mkdir(exist_ok=True)
    while True:
        rows = q.get()
        try:
            with open(path / f"served-{time.strftime('%Y%m%d')}.jsonl", "a", encoding="utf-8") as f:
                f.writelines(json.dumps(r) + "\n" for r in rows)
            if not dry:
                insert("scratch", rows, timeout=10)
        except Exception as e:
            print(f"log failed: {str(e)[:200]}", flush=True)


def main() -> None:
    dry = "--dry" in sys.argv
    state = State()
    state.load()
    state.start()
    logs: queue.Queue = queue.Queue()
    threading.Thread(target=log_writer, args=(logs, dry), daemon=True).start()

    seen: dict[str, float] = {}
    answered = late = 0
    report_at = time.time() + 30
    print(f"serving as {VERSION} ({'DRY RUN' if dry else 'LIVE'})", flush=True)
    while True:
        t0 = time.time()
        try:
            fresh = [r for r in query(NEW_REQUESTS, timeout=3) if r["id"] not in seen]
            todo = []
            for r in fresh:
                seen[r["id"]] = t0
                state.request_user[r["id"]] = (r["user"], t0)
                if int(r["now_ms"]) - int(r["ts_ms"]) > MAX_AGE_MS:
                    late += 1
                else:
                    todo.append(r)
            if todo:
                pairs = [answer(state, r) for r in todo]
                rows = [p[0] for p in pairs]
                if dry:
                    for row, log in pairs[:2]:
                        print(log["arm"], list(zip(row["items"], log["tiers"])), flush=True)
                else:
                    try:
                        insert("submissions", rows, timeout=2.5)
                    except Exception as e:  # one immediate retry: a duplicate answer is harmless, a missing one is not
                        print(f"insert failed, retrying: {str(e)[:200]}", flush=True)
                        insert("submissions", rows, timeout=2.5)
                answered += len(rows)
                logs.put([p[1] for p in pairs])
            if len(seen) > 5000:
                cutoff = t0 - 60
                seen = {k: v for k, v in seen.items() if v > cutoff}
            if t0 > report_at:
                print(f"{time.strftime('%H:%M:%S')} answered={answered} skipped_late={late} "
                      f"unavailable={len(state.unavailable)} loop={1000 * (time.time() - t0):.0f}ms", flush=True)
                report_at = t0 + 60
        except Exception as e:  # shoppers keep arriving: log and go on
            print(f"loop error: {str(e)[:200]}", flush=True)
            time.sleep(0.2)
        time.sleep(max(0.0, POLL_EVERY - (time.time() - t0)))


if __name__ == "__main__":
    while True:  # if anything escapes the loop, start again rather than leave shoppers to the fallback
        try:
            main()
        except Exception as e:
            print(f"fatal: {str(e)[:300]} — restarting in 2 s", flush=True)
            time.sleep(2)
