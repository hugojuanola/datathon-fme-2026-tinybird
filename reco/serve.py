"""The live loop: pull new requests → rank → push answers. This process *is* our submission.

    python -m reco.serve              # answer live traffic (only ONE instance may answer at a time)
    python -m reco.serve --dry        # same, but print instead of inserting: safe for testing
    python -m reco.serve --standby    # load everything, then wait for the file $SKORE_LOGS_DIR/GO before
                                      # answering: start the new version, stop the old one, create GO → no gap

Design goals, in order: never die, never send an invalid answer, answer fast, be explainable.

Speed and resilience. RawTree usually answers in ~0.2 s, but now and then a call takes seconds. So
nothing waits for a single call:

    3 pollers   read shop.requests on staggered schedules (one poll every 0.2 s overall); a slow response
                delays only its own poll, the next one is already on its way
    1 ranker    this thread: de-duplicates what the pollers bring, ranks (≈10 ms per request)
    2 senders   insert the answers; a slow insert does not hold the next batch

Typical latency from the request ts is ~1 s of the 3 s allowed.
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

# (model_version written with each answer and shown on the public leaderboard, policy, % of the traffic)
ARMS = (("skore_money_v5", "model", 80), ("skore_money_v5_explore", "explore", 20))
POLLERS = 3
POLL_EVERY = 0.2        # seconds between polls of shop.requests, all pollers together
SENDERS = 2
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
    bucket = zlib.crc32(b"arm:" + request_id.encode()) % 100
    for version, policy, share in ARMS:
        bucket -= share
        if bucket < 0:
            return version, policy
    return ARMS[0][:2]


def answer(state: State, ranker: Ranker | None, req: dict) -> tuple[dict, dict]:
    """One submission row and one log row for a request. Never raises, never returns an invalid list."""
    version, policy = arm_of(req["id"])
    items: list[str] = []
    for attempt in ([policy, "rules"] if policy != "rules" and ranker else ["rules"]):
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


def poller(out: queue.Queue, offset: float) -> None:
    """One of the staggered readers of shop.requests. Puts (seconds the query took, rows) or the exception."""
    time.sleep(offset)
    period = POLLERS * POLL_EVERY
    while True:
        t0 = time.time()
        try:
            rows = query(NEW_REQUESTS, timeout=2.5)
            out.put((time.time() - t0, rows))
        except Exception as e:
            out.put(e)
        time.sleep(max(0.0, period - (time.time() - t0)))


def sender(q: queue.Queue) -> None:
    """Insert the answers. Batches that pile up while an insert is in flight go out together."""
    while True:
        rows = q.get()
        while not q.empty():
            try:
                rows = rows + q.get_nowait()
            except queue.Empty:
                break
        for attempt in (1, 2):  # one immediate retry: a duplicate answer is harmless, a missing one is not
            try:
                insert("submissions", rows, timeout=2.0)
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
    state.keep_journal = not dry
    state.load()
    state.start()
    if standby:
        print(f"standby: ready, waiting for {go}", flush=True)
        while not go.exists():
            time.sleep(0.05)
        go.unlink(missing_ok=True)

    polls: queue.Queue = queue.Queue()
    answers: queue.Queue = queue.Queue()
    logs: queue.Queue = queue.Queue()
    for k in range(POLLERS):
        threading.Thread(target=poller, args=(polls, k * POLL_EVERY), daemon=True).start()
    for _ in range(SENDERS):
        threading.Thread(target=sender, args=(answers,), daemon=True).start()
    threading.Thread(target=log_writer, args=(logs, dry), daemon=True).start()

    seen: dict[str, float] = {}
    answered = late = held = failed_polls = 0
    rank_ms: list[float] = []
    poll_ms: list[float] = []
    report_at = time.time() + 30
    print(f"serving {[f'{v} {share}%' for v, _, share in ARMS]} ({'DRY RUN' if dry else 'LIVE'})", flush=True)
    while True:
        try:
            try:
                result = polls.get(timeout=2.0)
            except queue.Empty:
                print("no poll came back for 2 s", flush=True)
                continue
            if isinstance(result, Exception):
                failed_polls += 1
                continue
            took, rows = result
            poll_ms.append(1000 * took)
            now, todo = time.time(), []
            for r in rows:
                if r["id"] in seen:
                    continue
                ts_ms, age = int(r["ts_ms"]), int(r["now_ms"]) - int(r["ts_ms"])
                if age <= HOLD_UNTIL_MS and not state.stock_is_fresh_for(ts_ms):
                    held += 1          # not marked as seen: a later poll picks it up again
                    continue
                seen[r["id"]] = now
                state.request_user[r["id"]] = (r["user"], now)
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
                seen = {k: v for k, v in seen.items() if v > now - 60}
            if now > report_at:
                print(f"{time.strftime('%H:%M:%S')} answered={answered} skipped_late={late} held={held} "
                      f"failed_polls={failed_polls} poll_ms avg={sum(poll_ms) / max(len(poll_ms), 1):.0f} "
                      f"max={max(poll_ms, default=0):.0f} rank_ms/request avg={sum(rank_ms) / max(len(rank_ms), 1):.0f} "
                      f"max={max(rank_ms, default=0):.0f} unavailable={len(state.unavailable)} "
                      f"shoppers={len(state.shoppers)}", flush=True)
                rank_ms.clear()
                poll_ms.clear()
                report_at = now + 60
        except Exception as e:  # shoppers keep arriving: log and go on
            print(f"loop error: {str(e)[:200]}", flush=True)
            time.sleep(0.2)


if __name__ == "__main__":
    while True:  # if anything escapes the loop, start again rather than leave shoppers to the fallback
        try:
            main()
        except Exception as e:
            print(f"fatal: {str(e)[:300]} — restarting in 2 s", flush=True)
            time.sleep(2)
