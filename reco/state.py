"""Everything the recommender knows about the store, loaded from RawTree and kept fresh.

Four background threads keep the state current while the serving loop only reads it:

    catalog   every 1 s    new products, price changes, stock-outs   (shop.catalog_updates)
    events    every 1 s    who carted / bought what, live            (shop.events)
    feedback  every 2 s    what our own carousel sold                (team_NN.feedback)
    trends    every 60 s   live popularity per product               (shop.events)

All heavy lifting (aggregations over the 12 M-row history) is done in SQL inside RawTree; only
the compact results travel to this process.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass

from reco.rawtree import TEAM, query, query_tsv


@dataclass(slots=True)
class Product:
    category: str
    subcategory: str
    brand: str
    price: float
    base_price: float   # price at the start of the stream: price / base_price < 1 means a discount
    is_new: bool        # added during the event (cold-start product)


USER_ITEMS = """
SELECT user_id::String AS u, product_id::String AS p,
       countIf(event_type = 'purchase') AS np, toUnixTimestamp(max(ts::DateTime64(3))) AS t
FROM {table}
WHERE event_type != 'view' AND cityHash64(user_id::String) % {n} = {k}
GROUP BY u, p"""

POPULARITY = """
SELECT product_id::String AS p, countIf(event_type = 'purchase') AS n
FROM {table} {where}
GROUP BY p"""


class State:
    def __init__(self) -> None:
        self.products: dict[str, Product] = {}
        self.unavailable: set[str] = set()
        self.catalog_cursor = 0                       # ms of the last catalog update applied
        self.hist_pop: dict[str, float] = {}          # share of all-time purchases
        self.live_pop: dict[str, float] = {}          # share of purchases in the live window
        self.best: list[str] = []                     # all products, most popular first
        self.by_sub: dict[str, list[str]] = {}
        self.by_cat: dict[str, list[str]] = {}
        self.carted: dict[str, dict[str, int]] = defaultdict(dict)   # user -> {product: last ts (s)}
        self.purchased: dict[str, set[str]] = defaultdict(set)       # user -> products already bought
        self.request_user: dict[str, tuple[str, float]] = {}         # request_id -> (user, seen at)
        self.events_cursor = 0                        # s of the last live event applied
        self.started = time.time()

    # ---------------------------------------------------------------- bootstrap
    def load(self) -> None:
        t0 = time.time()
        for r in query("""SELECT product_id::String AS p, category::String AS c, subcategory::String AS s,
                                 brand::String AS b, price_eur::Float64 AS price FROM shop.catalog"""):
            self.products[r["p"]] = Product(r["c"], r["s"], r["b"], r["price"], r["price"], False)
        self.refresh_catalog()
        self._load_user_items("shop.history_events", chunks=6)
        self._load_user_items("shop.events", chunks=2)
        self.events_cursor = int(time.time()) - 60    # the tail re-reads the last minute: adds are idempotent
        for r in query(f"""SELECT r.user_id::String AS u, f.purchased::String AS p
                           FROM {TEAM}.feedback AS f
                           INNER JOIN shop.requests AS r ON r.request_id::String = f.request_id::String
                           WHERE f.purchased != '' AND f.request_id != '__init__'"""):
            self.purchased[r["u"]].add(r["p"])
        rows = query(POPULARITY.format(table="shop.history_events", where=""))
        total = sum(int(r["n"]) for r in rows) or 1
        self.hist_pop = {r["p"]: int(r["n"]) / total for r in rows}
        self.refresh_trends()
        print(f"state loaded in {time.time() - t0:.1f}s: {len(self.products)} products, "
              f"{len(self.unavailable)} unavailable, {len(self.carted)} users with carts, "
              f"{len(self.purchased)} users with purchases", flush=True)

    def _load_user_items(self, table: str, chunks: int) -> None:
        for k in range(chunks):
            df = query_tsv(USER_ITEMS.format(table=table, n=chunks, k=k), timeout=60)
            for u, p, np_, t in zip(df.u.values, df.p.values, df.np.values, df.t.values):
                if np_ > 0:
                    self.purchased[u].add(p)
                else:
                    self.carted[u][p] = int(t)

    # ---------------------------------------------------------------- refreshers
    def refresh_catalog(self) -> None:
        """Apply catalog updates newer than the cursor: new products, prices, stock."""
        rows = query(f"""SELECT toUnixTimestamp64Milli(ts::DateTime64(3)) AS t, change::String AS change,
                                product_id::String AS p, category::String AS c, subcategory::String AS s,
                                brand::String AS b, price_eur::Float64 AS price, is_active::Bool AS active
                         FROM shop.catalog_updates
                         WHERE ts::DateTime64(3) > fromUnixTimestamp64Milli({max(0, self.catalog_cursor - 2000)})
                         ORDER BY t""")
        new_products = False
        for r in rows:
            p, known = r["p"], self.products.get(r["p"])
            if known is None:
                self.products[p] = Product(r["c"], r["s"], r["b"], r["price"], r["price"], True)
                new_products = True
            else:
                known.price = r["price"]
            # unavailable = out of stock or inactive; anything else (back_in_stock, price_change on an
            # active product, new_product) makes it available again
            if r["change"] == "out_of_stock" or not r["active"]:
                self.unavailable.add(p)
            elif r["change"] in ("back_in_stock", "new_product"):
                self.unavailable.discard(p)
            self.catalog_cursor = max(self.catalog_cursor, int(r["t"]))
        if new_products and self.best:
            self._rank()

    def refresh_events(self) -> None:
        """Tail the live stream: carts and purchases per user."""
        rows = query(f"""SELECT toUnixTimestamp(ts::DateTime64(3)) AS t, event_type::String AS ev,
                                user_id::String AS u, product_id::String AS p
                         FROM shop.events
                         WHERE event_type != 'view' AND ts::DateTime64(3) > fromUnixTimestamp({self.events_cursor - 5})
                         ORDER BY t""")
        for r in rows:
            if r["ev"] == "purchase":
                self.purchased[r["u"]].add(r["p"])
                self.carted[r["u"]].pop(r["p"], None)
            elif r["p"] not in self.purchased[r["u"]]:
                self.carted[r["u"]][r["p"]] = int(r["t"])
            self.events_cursor = max(self.events_cursor, int(r["t"]))

    def refresh_feedback(self) -> None:
        """What our own carousel sold: those shoppers will not want the product again (satiation)."""
        rows = query(f"""SELECT request_id::String AS rid, purchased::String AS p FROM {TEAM}.feedback
                         WHERE purchased != '' AND ts::DateTime64(3) > now64(3) - INTERVAL 40 SECOND""")
        for r in rows:
            seen = self.request_user.get(r["rid"])
            if seen:
                self.purchased[seen[0]].add(r["p"])
                self.carted[seen[0]].pop(r["p"], None)
        cutoff = time.time() - 180
        for rid in [rid for rid, (_, t) in list(self.request_user.items()) if t < cutoff]:
            self.request_user.pop(rid, None)

    def refresh_trends(self) -> None:
        """Live popularity (last 3 h of the stream): the only signal new products have."""
        rows = query(POPULARITY.format(table="shop.events", where="WHERE ts::DateTime64(3) > now64(3) - INTERVAL 3 HOUR"))
        total = sum(int(r["n"]) for r in rows) or 1
        self.live_pop = {r["p"]: int(r["n"]) / total for r in rows}
        self._rank()

    def _rank(self) -> None:
        pop = {p: self.hist_pop.get(p, 0.0) + self.live_pop.get(p, 0.0) for p in self.products}
        best = sorted(pop, key=lambda p: (pop[p], p), reverse=True)
        by_sub, by_cat = defaultdict(list), defaultdict(list)
        for p in best:
            by_sub[self.products[p].subcategory].append(p)
            by_cat[self.products[p].category].append(p)
        self.best, self.by_sub, self.by_cat = best, dict(by_sub), dict(by_cat)

    # ---------------------------------------------------------------- threads
    def start(self) -> None:
        for fn, every in ((self.refresh_catalog, 1.0), (self.refresh_events, 1.0),
                          (self.refresh_feedback, 2.0), (self.refresh_trends, 60.0)):
            threading.Thread(target=self._loop, args=(fn, every), daemon=True, name=fn.__name__).start()

    @staticmethod
    def _loop(fn, every: float) -> None:
        while True:
            t0 = time.time()
            try:
                fn()
            except Exception as e:  # keep the last good state and try again
                print(f"{fn.__name__} failed: {str(e)[:200]}", flush=True)
            time.sleep(max(0.05, every - (time.time() - t0)))
