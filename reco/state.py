"""Everything the recommender knows about the store, kept fresh from RawTree.

The state is event-sourced: it is the 60-day history plus every live event applied one by one, with the
same `Shopper` updates that `offline/build_dataset.py` uses to build the training set. So the model
sees live exactly the numbers it was trained on.

Start-up is deliberately light, because heavy queries (or anything else that hogs the machine or the
uplink) starve the serving loop:

    history   loaded from a local file, $SKORE_DATA_DIR/cache/history.pkl (python -m offline.build_cache).
              Without it, the same numbers are aggregated in SQL inside RawTree (slower: minutes).
    live      replayed from a local journal of the stream, then caught up from shop.events in small pages.

While serving, three threads keep it current with small, bounded queries:

    catalog   every 1 s    new products, price changes, stock-outs      (shop.catalog_updates)
              (every 0.2 s around the 5-minute marks, when stock changes land)
    events    every 1 s    every view / cart / purchase, per shopper    (shop.events) → journal;
                           once a minute it rebuilds the Catalog snapshot (live popularity, new products)
    feedback  every 2 s    what our own carousel sold (satiation)       (team_NN.feedback)
"""
from __future__ import annotations

import pickle
import threading
import time
from dataclasses import dataclass

import numpy as np

from reco.features import Catalog, Shopper
from reco.rawtree import DATA, TEAM, query, query_rows, query_tsv

STOCK_PERIOD_MS = 300_000   # stock changes land every 5 minutes on the dot…
STOCK_VISIBLE_MS = 800      # …and become queryable about this long after (measured 14 Nov 13:00 UTC)
PAGE = 50_000               # live events per catch-up query
CACHE = DATA / "cache"
JOURNAL = CACHE / "journal"


@dataclass(slots=True)
class Product:
    category: str
    subcategory: str
    brand: str
    price: float
    added: int = 0      # unix seconds when it was added during the event; 0 = in the original catalogue


EVENTS_PAGE = """
SELECT toUnixTimestamp64Milli(ts::DateTime64(3)) AS t, substring(event_type::String, 1, 1) AS ev,
       user_id::String AS u, product_id::String AS p
FROM shop.events
WHERE ts::DateTime64(3) > fromUnixTimestamp64Milli({cursor})
ORDER BY ts LIMIT {limit}"""

# --- SQL fallback for the history, used only when the local cache is missing -------------------------
SHOPPER_SUBCATEGORIES = """
SELECT e.u AS u, c.s AS s, countIf(e.ev = 'view') AS v, countIf(e.ev = 'add_to_cart') AS a,
       countIf(e.ev = 'purchase') AS p, sumIf(c.lp, e.ev = 'purchase') AS lp
FROM (SELECT user_id::String AS u, product_id::String AS pid, event_type::String AS ev
      FROM shop.history_events WHERE cityHash64(user_id::String) % {n} = {k}) AS e
INNER JOIN (SELECT product_id::String AS pid, subcategory::String AS s, log(greatest(price_eur::Float64, 0.5)) AS lp
            FROM shop.catalog) AS c ON c.pid = e.pid
GROUP BY u, s"""

SHOPPER_PRODUCTS = """
SELECT user_id::String AS u, product_id::String AS p,
       countIf(event_type = 'purchase') AS np, toUnixTimestamp(max(ts::DateTime64(3))) AS t
FROM shop.history_events
WHERE event_type != 'view' AND cityHash64(user_id::String) % {n} = {k}
GROUP BY u, p"""

PRODUCT_COUNTS = """
SELECT product_id::String AS p, countIf(event_type = 'view') AS v, countIf(event_type = 'add_to_cart') AS a,
       countIf(event_type = 'purchase') AS n
FROM shop.history_events
GROUP BY p"""


class State:
    def __init__(self) -> None:
        self.products: dict[str, Product] = {}
        self.pids: list[str] = []                 # append-only: a product's index never changes
        self.pos: dict[str, int] = {}
        self.unavailable: set[str] = set()
        self.catalog_cursor = 0                   # ms of the last catalog update applied
        self.clock_offset = 0.0                   # RawTree's clock minus ours, seconds
        self.hist_counts: dict[str, tuple[float, float, float]] = {}   # product -> (views, carts, purchases), 60 days
        self.live_counts: dict[str, list[float]] = {}                  # same, live stream so far
        self.buy_minutes: dict[int, int] = {}     # minute of the stream -> purchases (for new products' exposure)
        self.catalog: Catalog | None = None       # immutable snapshot, swapped atomically
        self.best: list[str] = []                 # all products, most popular first
        self.shoppers: dict[str, Shopper] = {}
        self.request_user: dict[str, tuple[str, float]] = {}   # request_id -> (user, seen at)
        self.events_cursor = 0                    # ms of the newest live event applied
        self._recent: dict[tuple, int] = {}       # events of the last seconds, to apply each exactly once
        self._sub_of: list[int] = []
        self._log_price_of: list[float] = []
        self._journal = None
        self.keep_journal = True                  # False for dry runs: they must not leave journal segments
        self._snapshot_at = 0.0

    # ---------------------------------------------------------------- bootstrap
    def load(self) -> None:
        t0 = time.time()
        for r in query("""SELECT product_id::String AS p, category::String AS c, subcategory::String AS s,
                                 brand::String AS b, price_eur::Float64 AS price FROM shop.catalog ORDER BY p"""):
            self._add_product(r["p"], Product(r["c"], r["s"], r["b"], r["price"]))
        self.refresh_catalog()
        self.clock_offset = int(query("SELECT toUnixTimestamp64Milli(now64(3)) AS t")[0]["t"]) / 1000 - time.time()

        cache = self._read_cache()
        if cache:
            self.hist_counts, self.shoppers = cache["counts"], cache["shoppers"]
            self._snapshot((cache["cat_names"], cache["sub_names"], cache["brand_names"]))
        else:
            print("no usable history cache: aggregating the history in RawTree (slow)", flush=True)
            self.hist_counts = {r["p"]: (float(r["v"]), float(r["a"]), float(r["n"])) for r in query(PRODUCT_COUNTS)}
            self._snapshot()
            self._load_shoppers_sql()
        history_s = time.time() - t0

        replayed = self._replay_journal()
        if self.keep_journal:
            JOURNAL.mkdir(parents=True, exist_ok=True)
            self._journal = open(JOURNAL / f"events-{self.events_cursor}.tsv", "a", encoding="utf-8")
        fetched = self._catch_up()
        for r in query(f"""SELECT r.user_id::String AS u, f.purchased::String AS p
                           FROM {TEAM}.feedback AS f
                           INNER JOIN shop.requests AS r ON r.request_id::String = f.request_id::String
                           WHERE f.purchased != '' AND f.request_id != '__init__'"""):
            if r["p"] in self.pos:
                self.shopper(r["u"]).sold(self.pos[r["p"]])
        self._snapshot()
        print(f"state loaded in {time.time() - t0:.1f}s (history {history_s:.1f}s, journal {replayed:,} events, "
              f"fetched {fetched:,}): {len(self.pids)} products, {len(self.unavailable)} unavailable, "
              f"{len(self.shoppers)} shoppers", flush=True)

    def _add_product(self, pid: str, product: Product) -> None:
        self.products[pid] = product
        self.pos[pid] = len(self.pids)
        self.pids.append(pid)

    def shopper(self, user: str) -> Shopper:
        s = self.shoppers.get(user)
        if s is None:
            s = self.shoppers[user] = Shopper()
        return s

    def _read_cache(self) -> dict | None:
        path = CACHE / "history.pkl"
        if not path.exists():
            return None
        with open(path, "rb") as f:
            cache = pickle.load(f)
        if cache.get("pids") != self.pids[:len(cache.get("pids", []))] or "brand_names" not in cache:
            print("history cache does not match the catalogue: ignoring it", flush=True)
            return None
        return cache

    def _load_shoppers_sql(self, chunks: int = 8) -> None:
        sub_id = {s: i for i, s in enumerate(self.catalog.sub_names)}
        for k in range(chunks):
            df = query_tsv(SHOPPER_SUBCATEGORIES.format(n=chunks, k=k), timeout=90)
            for u, s, v, a, p, lp in zip(df.u.values, df.s.values, df.v.values, df.a.values, df.p.values, df.lp.values):
                sh, sid = self.shopper(u), sub_id[s]
                sh.views += int(v)
                sh.carts += int(a)
                sh.purchases += int(p)
                sh.price_sum += float(lp)
                if v:
                    sh.sub_views[sid] = sh.sub_views.get(sid, 0) + int(v)
                if p:
                    sh.sub_purch[sid] = sh.sub_purch.get(sid, 0) + int(p)
            df = query_tsv(SHOPPER_PRODUCTS.format(n=chunks, k=k), timeout=90)
            for u, p, np_, t in zip(df.u.values, df.p.values, df.np.values, df.t.values):
                sh, i = self.shopper(u), self.pos[p]
                if np_ > 0:
                    sh.bought.add(i)
                    sh.carted.pop(i, None)
                elif i not in sh.bought:
                    sh.carted[i] = int(t)
        for u, p in query_rows("""SELECT user_id::String, purchased::String FROM shop.history_sessions
                                  WHERE purchased IS NOT NULL""", timeout=60):
            if p in self.pos:     # what the old carousel sold is satiated too
                self.shopper(u).sold(self.pos[p])

    # ---------------------------------------------------------------- live events
    def _apply(self, t: int, ev: str, user: str, pid: str) -> None:
        """One live event → the shopper's running totals and the product's live counts."""
        i = self.pos.get(pid)
        if i is None or i >= len(self._sub_of):
            return
        sh = self.shoppers.get(user)
        if sh is None:
            sh = self.shoppers[user] = Shopper()
        counts = self.live_counts.get(pid)
        if counts is None:
            counts = self.live_counts[pid] = [0.0, 0.0, 0.0]
        if ev == "v":
            sh.view(self._sub_of[i])
            counts[0] += 1
        elif ev == "a":
            sh.cart(i, t // 1000)
            counts[1] += 1
        else:
            sh.buy(i, self._sub_of[i], self._log_price_of[i])
            counts[2] += 1
            minute = t // 60000
            self.buy_minutes[minute] = self.buy_minutes.get(minute, 0) + 1

    def _replay_journal(self) -> int:
        """Re-apply the live events saved by previous runs. Segments may overlap in time (a standby process
        and the one it replaces both write): a segment only contributes what is newer than those before it."""
        n = 0
        if JOURNAL.exists():
            for path in sorted(JOURNAL.glob("events-*.tsv"), key=lambda p: int(p.stem.split("-")[1])):
                floor = self.events_cursor
                with open(path, encoding="utf-8") as f:
                    for line in f:
                        parts = line.rstrip("\n").split("\t")
                        if len(parts) != 4:
                            continue
                        t = int(parts[0])
                        if t > floor:
                            self._apply(t, parts[1], parts[2], parts[3])
                            n += 1
                            if t > self.events_cursor:
                                self.events_cursor = t
        return n

    def _ingest(self, rows: list[list[str]]) -> int:
        """Apply the events not seen yet, append them to the journal, advance the cursor."""
        lines = []
        for t_, ev, user, pid in rows:
            key = (t_, user, pid, ev)
            if key in self._recent:
                continue
            t = int(t_)
            self._recent[key] = t
            self._apply(t, ev, user, pid)
            lines.append(f"{t_}\t{ev}\t{user}\t{pid}\n")
            if t > self.events_cursor:
                self.events_cursor = t
        if lines and self._journal:
            self._journal.writelines(lines)
            self._journal.flush()
        if len(self._recent) > 20000:
            cutoff = self.events_cursor - 10000
            self._recent = {k: t for k, t in self._recent.items() if t > cutoff}
        return len(lines)

    def _catch_up(self) -> int:
        """From the cursor to now, in pages small enough not to disturb whoever is serving."""
        n = 0
        while True:
            rows = query_rows(EVENTS_PAGE.format(cursor=self.events_cursor, limit=PAGE), timeout=60)
            full = len(rows) == PAGE
            if full:    # the last millisecond of a full page may be incomplete: it comes back in the next page
                rows = [r for r in rows if r[0] != rows[-1][0]]
                self.events_cursor = max(self.events_cursor, int(rows[-1][0]))
            n += self._ingest(rows)
            if not full:
                return n
            time.sleep(0.1)

    def refresh_events(self) -> None:
        """Tail the live stream (re-reading the last 3 s for late rows; each event is applied once)."""
        self._ingest(query_rows(EVENTS_PAGE.format(cursor=self.events_cursor - 3000, limit=PAGE), timeout=5))
        if time.time() - self._snapshot_at > 60:
            self._snapshot()

    # ---------------------------------------------------------------- catalog and feedback
    def refresh_catalog(self) -> None:
        """Apply catalog updates newer than the cursor: new products, prices, stock."""
        rows = query(f"""SELECT toUnixTimestamp64Milli(ts::DateTime64(3)) AS t, change::String AS change,
                                product_id::String AS p, category::String AS c, subcategory::String AS s,
                                brand::String AS b, price_eur::Float64 AS price, is_active::Bool AS active
                         FROM shop.catalog_updates
                         WHERE ts::DateTime64(3) > fromUnixTimestamp64Milli({max(0, self.catalog_cursor - 2000)})
                         ORDER BY t, p""", timeout=5)
        changed = False
        for r in rows:
            p, known = r["p"], self.products.get(r["p"])
            if known is None:
                self._add_product(p, Product(r["c"], r["s"], r["b"], r["price"], int(r["t"]) // 1000))
                changed = True
            elif known.price != r["price"]:
                known.price = r["price"]
                changed = True
            # unavailable = out of stock or inactive; back_in_stock / new_product make it available again
            if r["change"] == "out_of_stock" or not r["active"]:
                self.unavailable.add(p)
            elif r["change"] in ("back_in_stock", "new_product"):
                self.unavailable.discard(p)
            self.catalog_cursor = max(self.catalog_cursor, int(r["t"]))
        if changed and self.catalog is not None:
            self._snapshot()

    def stock_is_fresh_for(self, request_ts_ms: int) -> bool:
        """False for a request that falls right after a 5-minute mark whose stock changes we have not seen yet."""
        mark = request_ts_ms - request_ts_ms % STOCK_PERIOD_MS
        return request_ts_ms - mark > 2000 or self.catalog_cursor >= mark

    def refresh_feedback(self) -> None:
        """What our own carousel sold: those shoppers will not want the product again (satiation)."""
        rows = query(f"""SELECT request_id::String AS rid, purchased::String AS p FROM {TEAM}.feedback
                         WHERE purchased != '' AND ts::DateTime64(3) > now64(3) - INTERVAL 40 SECOND""", timeout=5)
        for r in rows:
            seen = self.request_user.get(r["rid"])
            if seen and r["p"] in self.pos:
                self.shopper(seen[0]).sold(self.pos[r["p"]])
        cutoff = time.time() - 180
        for rid in [rid for rid, (_, t) in list(self.request_user.items()) if t < cutoff]:
            self.request_user.pop(rid, None)

    def _snapshot(self, names: tuple[list[str], list[str], list[str]] | None = None) -> None:
        """A fresh Catalog: current products and prices, history + live statistics."""
        pids = list(self.pids)
        products = [self.products[p] for p in pids]
        zero = (0.0, 0.0, 0.0)
        counts = np.array([np.add(self.hist_counts.get(p, zero), self.live_counts.get(p, zero)) for p in pids]).T
        minutes = sorted(list(self.buy_minutes.items()))
        live_total = sum(n for _, n in minutes)
        exposure = np.full(len(pids), sum(c[2] for c in self.hist_counts.values()) + live_total, dtype=float)
        for i, product in enumerate(products):
            if product.added:   # a new product has only been exposed to the purchases made since it appeared
                exposure[i] = sum(n for m, n in minutes if m >= product.added // 60)
        prev = self.catalog
        if names is None and prev is not None:
            names = (prev.cat_names, prev.sub_names, prev.brand_names)
        cat = Catalog(pids, [p.category for p in products], [p.subcategory for p in products],
                      [p.brand for p in products], np.array([p.price for p in products]),
                      counts[0], counts[1], counts[2], exposure=exposure, names=names)
        self._sub_of, self._log_price_of = cat.sub.tolist(), cat.log_price.tolist()
        self.best = [pids[i] for i in np.lexsort((np.arange(len(pids)), -cat.share))]
        self.catalog = cat
        self._snapshot_at = time.time()

    # ---------------------------------------------------------------- threads
    def start(self) -> None:
        for fn, every in ((self.refresh_catalog, 1.0), (self.refresh_events, 1.0), (self.refresh_feedback, 2.0)):
            threading.Thread(target=self._loop, args=(fn, every), daemon=True, name=fn.__name__).start()

    def _loop(self, fn, every: float) -> None:
        while True:
            t0 = time.time()
            try:
                fn()
            except Exception as e:  # keep the last good state and try again
                print(f"{fn.__name__} failed: {str(e)[:200]}", flush=True)
            pause = every
            if fn == self.refresh_catalog:   # poll faster while the stock changes of a 5-minute mark are due
                since_mark = ((time.time() + self.clock_offset) * 1000) % STOCK_PERIOD_MS
                if since_mark < 4000 or since_mark > STOCK_PERIOD_MS - 500:
                    pause = 0.2
            time.sleep(max(0.05, pause - (time.time() - t0)))
