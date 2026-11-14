"""The live loop: pull new requests → rank → push answers. This process *is* our submission.

    python -m reco.serve              # answer live traffic (only ONE instance may answer at a time)
    python -m reco.serve --dry        # same, but print instead of inserting: safe for testing
    python -m reco.serve --standby    # load everything, then wait for the file $SKORE_LOGS_DIR/GO before
                                      # answering: start the new version, stop the old one, create GO → no gap

Design goals, in order: never die, never send an invalid answer, answer fast, be explainable.

Speed and resilience. RawTree usually answers in ~0.2 s, but now and then a call takes seconds. So
nothing waits for a single call:

    4 pollers   read shop.requests on staggered schedules (one poll every 0.15 s overall); a slow response
                delays only its own poll, the next one is already on its way
    1 ranker    this thread: de-duplicates what the pollers bring, ranks (≈25 ms per request)
    4 senders   insert the answers, each on its own connection. An insert that has not come back after
                0.6 s is sent again on another connection (measured: a duplicate answer is harmless, and
                the home uplink sometimes stalls a single connection for seconds)

Typical latency from the request ts is ~1 s of the 3 s allowed.
"""
from __future__ import annotations

import json
import queue
import sys
import threading
import time
import zlib

from reco.priority import foreground, stay_awake
from reco.rawtree import LOGS, ROOT, insert, query
from reco.recommend import Ranker, is_valid, recommend, safe_list
from reco.state import State

# (model_version written with each answer and shown on the public leaderboard, policy, ranker in models/,
#  how much of a live trend to apply (0 = ignore trends: see recommend), % of the traffic).
#  A ranker "A|B" routes by kind of request: A answers the cold ones (see is_cold), B the rest.
ARMS = (("skore_money_v11", "model", "v9w|v9", 0.0, 33), ("skore_money_v14", "model", "v9w|v9", 1.0, 34),
        ("skore_money_v13", "model", "v9w|v10", 0.0, 33))
POLLERS = 4
POLL_EVERY = 0.15       # seconds between polls of shop.requests, all pollers together
SENDERS = 4
HEDGE_AFTER = 0.6       # seconds before an insert that has not come back is sent again on another connection
MAX_AGE_MS = 2800       # an answer must land within 3000 ms of the request ts: do not bother after this
HOLD_UNTIL_MS = 1600    # a request right after a 5-minute mark waits (at most this long) for the new stock list

NEW_REQUESTS = """
SELECT request_id::String AS id, toUnixTimestamp64Milli(ts::DateTime64(3)) AS ts_ms, user_id::String AS user,
       context.page::String AS page, context.device::String AS device, context.region::String AS region,
       arrayMap(v -> v.product_id::String, recent_views::Array(JSON)) AS rv,
       is_new_user::Bool AS is_new, toUnixTimestamp64Milli(now64(3)) AS now_ms
FROM shop.requests
WHERE ts > now64(3) - INTERVAL 4 SECOND
ORDER BY ts"""


def arm_of(request_id: str) -> tuple[str, str, str, float]:
    """Deterministic split on the request id, so every variant sees the same kind of traffic."""
    bucket = zlib.crc32(b"arm:" + request_id.encode()) % 100
    for version, policy, ranker, trend, share in ARMS:
        bucket -= share
        if bucket < 0:
            return version, policy, ranker, trend
    return ARMS[0][:4]


def is_cold(state: State, req: dict) -> bool:
    """The organisers' definition of a cold request: a new shopper, or a product added during the event among
    the recent views. These are the requests the old carousel log knows nothing about."""
    if str(req.get("is_new")).lower() in ("true", "1"):
        return True
    cat = state.catalog
    return any(bool(cat.is_new[cat.pos[p]]) for p in req["rv"] if p in cat.pos)


def answer(state: State, rankers: dict[str, Ranker], req: dict) -> tuple[dict, dict]:
    """One submission row and one log row for a request. Never raises, never returns an invalid list."""
    version, policy, name, trend = arm_of(req["id"])
    cold = None
    if "|" in name:
        try:
            cold = is_cold(state, req)
        except Exception as e:
            print(f"is_cold failed for {req['id']}: {str(e)[:200]}", flush=True)
            cold = False
        name = name.split("|")[0 if cold else 1]
    ranker = rankers.get(name)
    items: list[str] = []
    for attempt in ([policy, "rules"] if policy != "rules" and ranker else ["rules"]):
        try:
            items, why = recommend(state, ranker, req, attempt, trend=trend)
            if is_valid(state, items):
                policy = attempt
                break
            raise ValueError(f"invalid list {items}")
        except Exception as e:
            print(f"{attempt} failed for {req['id']}: {str(e)[:200]}", flush=True)
            items = []
    if not items:
        items, why, policy = safe_list(state), ["safe"] * 10, "safe"
    log = {"kind": "served", "request_id": req["id"], "ts_ms": req["ts_ms"], "user_id": req["user"],
           "model_version": version, "policy": policy, "ranker": name, "cold": cold, "items": items, "tiers": why}
    trending = state.trend
    if trending:    # what the detector saw when this request was answered, whether or not this arm used it
        names = state.catalog.sub_names
        log["trending"] = {names[s]: round(v, 1) for s, v in trending.items() if s < len(names)}
    return {"request_id": req["id"], "items": items, "model_version": version}, log


def selftest(state: State, rankers: dict[str, Ranker]) -> None:
    """Before taking over: every arm answers a few real requests, as things are and with a made-up trend."""
    try:
        rows = query(NEW_REQUESTS, timeout=5)[:12]
        cat = state.catalog
        fake = {int(max(cat.by_sub, key=lambda s: len(cat.by_sub[s]))): 5.0}
        for version, policy, name, trend, _ in ARMS:
            for label, trending in (("live trend", None), ("made-up trend", fake)):
                valid = shown = 0
                for r in rows:
                    ranker = rankers.get(name.split("|")[0 if is_cold(state, r) else -1])
                    items, why = recommend(state, ranker, r, policy if ranker else "rules", trend=trend, trending=trending)
                    valid += is_valid(state, items)
                    shown += why.count("t")
                print(f"selftest {version} ({label}): {valid}/{len(rows)} valid lists, {shown} trending products shown",
                      flush=True)
    except Exception as e:
        print(f"selftest failed: {str(e)[:300]}", flush=True)


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


class Batch:
    """Answers on their way to RawTree. `done` is set by whichever copy gets there first."""
    __slots__ = ("rows", "t0", "done", "copies")

    def __init__(self, rows: list[dict]) -> None:
        self.rows, self.t0, self.done, self.copies = rows, time.time(), threading.Event(), 0


def sender(q: queue.Queue, stats: dict) -> None:
    """Insert answers on this thread's own connection."""
    while True:
        batch = q.get()
        if batch.done.is_set() or time.time() - batch.t0 > 3.0:
            continue                    # another copy already made it, or it is too late to matter
        batch.copies += 1
        try:
            insert("submissions", batch.rows, timeout=2.0)
            batch.done.set()
        except Exception as e:
            stats["failed_inserts"] += 1
            if not batch.done.is_set():
                q.put(batch)            # try again, on whichever connection is free first
            if stats["failed_inserts"] % 20 == 1:
                print(f"insert failed ({stats['failed_inserts']} so far): {str(e)[:160]}", flush=True)


def hedger(inflight: queue.Queue, q: queue.Queue, stats: dict) -> None:
    """Send a second copy of any batch that has not been confirmed after HEDGE_AFTER seconds."""
    while True:
        batch = inflight.get()
        wait = batch.t0 + HEDGE_AFTER - time.time()
        if wait > 0:
            time.sleep(wait)            # batches arrive in time order, so sleeping in sequence is exact
        if not batch.done.is_set():
            stats["hedged"] += 1
            q.put(batch)


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
    stay_awake()
    LOGS.mkdir(parents=True, exist_ok=True)
    go = LOGS / "GO"
    go.unlink(missing_ok=True)
    rankers: dict[str, Ranker] = {}
    for name in sorted({part for arm in ARMS if arm[1] != "rules" for part in arm[2].split("|")}):
        try:
            folder, _, mode = name.partition("@")       # "v8@click" = models/v8, ranking by P(click) alone
            rankers[name] = Ranker(ROOT / "models" / folder, click_only=mode == "click")
        except Exception as e:  # no model, or a stale one: that arm falls back to the rules
            print(f"ranker {name} unavailable ({str(e)[:200]}): its arms use the rules", flush=True)
    state = State()
    state.keep_journal = not dry
    state.load()
    state.start()
    if standby:
        selftest(state, rankers)
        print(f"standby: ready, waiting for {go}", flush=True)
        while not go.exists():
            time.sleep(0.05)
        go.unlink(missing_ok=True)

    polls: queue.Queue = queue.Queue()
    answers: queue.Queue = queue.Queue()
    inflight: queue.Queue = queue.Queue()
    logs: queue.Queue = queue.Queue()
    stats = {"failed_inserts": 0, "hedged": 0}
    for k in range(POLLERS):
        threading.Thread(target=poller, args=(polls, k * POLL_EVERY), daemon=True).start()
    for _ in range(SENDERS):
        threading.Thread(target=sender, args=(answers, stats), daemon=True).start()
    threading.Thread(target=hedger, args=(inflight, answers, stats), daemon=True).start()
    threading.Thread(target=log_writer, args=(logs, dry), daemon=True).start()

    seen: dict[str, float] = {}
    answered = late = held = failed_polls = 0
    rank_ms: list[float] = []
    poll_ms: list[float] = []
    report_at = time.time() + 30
    print(f"serving {[f'{v} {share}%' + (f' trend^{t:g}' if t else '') for v, _, _, t, share in ARMS]} with rankers {sorted(rankers)} "
          f"({'DRY RUN' if dry else 'LIVE'})", flush=True)
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
                pairs = [answer(state, rankers, r) for r in todo]
                rank_ms.append(1000 * (time.time() - t1) / len(todo))
                if dry:
                    for row, log in pairs[:2]:
                        print(row["model_version"], list(zip(row["items"], log["tiers"])), flush=True)
                else:
                    batch = Batch([p[0] for p in pairs])
                    answers.put(batch)
                    inflight.put(batch)
                answered += len(pairs)
                logs.put([p[1] for p in pairs])
            if len(seen) > 5000:
                seen = {k: v for k, v in seen.items() if v > now - 60}
            if now > report_at:
                print(f"{time.strftime('%H:%M:%S')} answered={answered} skipped_late={late} held={held} "
                      f"failed_polls={failed_polls} failed_inserts={stats['failed_inserts']} hedged={stats['hedged']} "
                      f"poll_ms avg={sum(poll_ms) / max(len(poll_ms), 1):.0f} "
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
