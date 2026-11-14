"""The live loop: pull new requests → rank → push answers. This process *is* our submission.

    python -m reco.serve              # answer live traffic (only ONE instance may answer at a time)
    python -m reco.serve --dry        # same, but print instead of inserting: safe for testing
    python -m reco.serve --standby    # load everything, then wait for the file $SKORE_LOGS_DIR/GO before
                                      # answering: start the new version, stop the old one, create GO → no gap

Design goals, in order: never die, never send an invalid answer, answer fast, be explainable.

Speed: the loop only polls and ranks; answers are inserted by a second thread, so a slow insert never
delays the next poll. Typical latency from the request ts is ~1 s of the 3 s allowed.
"""
from __future__ import annotations

import json
import queue
import sys
import threading
import time
import zlib

from reco.priority import foreground
from reco.rawtree import LOGS, ROOT, insert, query
from reco.recommend import Ranker, is_valid, recommend, safe_list
from reco.state import State

# (model_version written with each answer and shown on the public leaderboard, policy)
ARMS = (("skore_money_v4", "rules"), ("skore_money_v5", "model"))
POLL_EVERY = 0.2        # seconds between polls of shop.requests
MAX_AGE_MS = 2800       # an answer must land within 3000 ms of the request ts: do not bother after this
HOLD_UNTIL_MS = 1600    # a request right after a 5-minute mark waits (at most this long) for the new stock list

NEW_REQUESTS = """
SELECT request_id::String AS id, toUnixTimestamp64Milli(ts::DateTime64(3)) AS ts_ms, user_id::String AS user,
       context.page::String AS page, context.device::String AS device, context.region::String AS region,
       arrayMap(v -> v.product_id::String, recent_views::Array(JSON)) AS rv,
       toUnixTimestamp64Milli(now64(3)) AS now_ms
FROM shop.requests
WHERE ts > now64(3) - INTERVAL 4 SECOND
ORDER BY ts"""


def arm_of(request_id: str) -> tuple[str, str]:
    """Deterministic split on the request id, so every variant sees the same kind of traffic."""
    return ARMS[zlib.crc32(request_id.encode()) % len(ARMS)]


def answer(state: State, ranker: Ranker | None, req: dict) -> tuple[dict, dict]:
    """One submission row and one log row for a request. Never raises, never returns an invalid list."""
    version, policy = arm_of(req["id"])
    items: list[str] = []
    for attempt in ([policy, "rules"] if policy == "model" and ranker else ["rules"]):
        try:
            items, why = recommend(state, ranker, req, attempt)
            if is_valid(state, items):
                policy = attempt
                break
            raise ValueError(f"invalid list {items}")
        except Exception as e:
            print(f"{attempt} failed for {req['id']}: {str(e)[:200]}", flush=True)
            items = []
    if not items:
        items, why, policy = safe_list(state), ["safe"] * 10, "safe"
    return ({"request_id": req["id"], "items": items, "model_version": version},
            {"kind": "served", "request_id": req["id"], "ts_ms": req["ts_ms"], "user_id": req["user"],
             "model_version": version, "policy": policy, "items": items, "tiers": why})


def sender(q: queue.Queue) -> None:
    """Insert the answers. Batches that pile up while an insert is in flight go out together."""
    while True:
        rows = q.get()
        while not q.empty():
            rows = rows + q.get()
        for attempt in (1, 2):  # one immediate retry: a duplicate answer is harmless, a missing one is not
            try:
                insert("submissions", rows, timeout=1.5)
                break
            except Exception as e:
                print(f"insert failed (attempt {attempt}): {str(e)[:200]}", flush=True)


def log_writer(q: queue.Queue, dry: bool) -> None:
    """Off the hot path: keep what we served (and why) in a local file and in team_NN.scratch."""
    while True:
        rows = q.get()
        try:
            with open(LOGS / f"served-{time.strftime('%Y%m%d')}.jsonl", "a", encoding="utf-8") as f:
                f.writelines(json.dumps(r) + "\n" for r in rows)
            if not dry:
                insert("scratch", rows, timeout=10)
        except Exception as e:
            print(f"log failed: {str(e)[:200]}", flush=True)


def main() -> None:
    dry, standby = "--dry" in sys.argv, "--standby" in sys.argv
    foreground()
    LOGS.mkdir(parents=True, exist_ok=True)
    go = LOGS / "GO"
    go.unlink(missing_ok=True)
    try:
        ranker = Ranker(ROOT / "models")
    except Exception as e:  # no model, or a stale one: serve everything with the rules
        print(f"no ranker ({str(e)[:200]}): every arm uses the rules", flush=True)
        ranker = None
    state = State()
    state.load()
    state.start()
    if standby:
        print(f"standby: ready, waiting for {go}", flush=True)
        while not go.exists():
            time.sleep(0.05)
        go.unlink(missing_ok=True)

    answers: queue.Queue = queue.Queue()
    logs: queue.Queue = queue.Queue()
    threading.Thread(target=sender, args=(answers,), daemon=True).start()
    threading.Thread(target=log_writer, args=(logs, dry), daemon=True).start()

    seen: dict[str, float] = {}
    answered = late = held = slow = 0
    rank_ms: list[float] = []
    report_at = time.time() + 30
    print(f"serving {[v for v, _ in ARMS]} ({'DRY RUN' if dry else 'LIVE'})", flush=True)
    while True:
        t0 = time.time()
        try:
            todo = []
            for r in query(NEW_REQUESTS, timeout=1.5):
                if r["id"] in seen:
                    continue
                ts_ms, age = int(r["ts_ms"]), int(r["now_ms"]) - int(r["ts_ms"])
                if age <= HOLD_UNTIL_MS and not state.stock_is_fresh_for(ts_ms):
                    held += 1          # not marked as seen: the next poll picks it up again
                    continue
                seen[r["id"]] = t0
                state.request_user[r["id"]] = (r["user"], t0)
                if age > MAX_AGE_MS:
                    late += 1
                else:
                    todo.append(r)
            if todo:
                t1 = time.time()
                pairs = [answer(state, ranker, r) for r in todo]
                rank_ms.append(1000 * (time.time() - t1) / len(todo))
                if dry:
                    for row, log in pairs[:2]:
                        print(row["model_version"], list(zip(row["items"], log["tiers"])), flush=True)
                else:
                    answers.put([p[0] for p in pairs])
                answered += len(pairs)
                logs.put([p[1] for p in pairs])
            if len(seen) > 5000:
                cutoff = t0 - 60
                seen = {k: v for k, v in seen.items() if v > cutoff}
            if time.time() - t0 > 1.0:
                slow += 1          # a healthy loop takes ~0.3 s: more than 1 s means something is starving it
            if t0 > report_at:
                print(f"{time.strftime('%H:%M:%S')} answered={answered} skipped_late={late} held={held} slow_loops={slow} "
                      f"unavailable={len(state.unavailable)} shoppers={len(state.shoppers)} "
                      f"rank_ms/request avg={sum(rank_ms) / max(len(rank_ms), 1):.0f} max={max(rank_ms, default=0):.0f} "
                      f"loop={1000 * (time.time() - t0):.0f}ms", flush=True)
                rank_ms.clear()
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
