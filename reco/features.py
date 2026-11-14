"""One definition of every model feature, used to build the training set AND to serve live.

Training/serving skew is the classic way a recommender that looks good offline fails live, so there is
exactly one `featurize()` and both paths call it. No feature is a product id or a user id: everything is
a count, a rate, a share or a match, so the model transfers to shoppers and products it has never seen.

    Catalog     the products as arrays, plus their organic statistics (popularity, cart rate…)
    Shopper     what one shopper has done so far (updated event by event)
    featurize   (catalog, shopper, request, candidate products) → feature matrix
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import log

import numpy as np

PAGES = {"home": 0, "category": 1, "product": 2}
DEVICES = {"web": 0, "ios": 1, "android": 2}
REGIONS = {r: i for i, r in enumerate(["Andalucía", "Aragón", "Canarias", "Castilla y León", "Catalunya",
                                       "Comunitat Valenciana", "Galicia", "Madrid", "Murcia", "País Vasco"])}

FEATURES = [
    # the product itself
    "pop", "view_share", "cart_rate", "buy_rate", "log_price", "pop_vs_sub", "pop_vs_cat",
    # how it matches this session
    "page", "n_recent", "same_cat", "same_sub", "same_brand", "in_recent", "is_last",
    "recent_sub_frac", "recent_cat_frac", "dprice_last", "dprice_recent",
    # how it matches this shopper
    "u_views", "u_purch", "u_buy_rate", "u_cat_view", "u_cat_purch", "u_sub_view", "u_sub_purch",
    "u_sub_purch_n", "u_carted", "u_dprice",
    # context
    "device", "region", "slot", "is_live",
]
CATEGORICAL = ["page", "device", "region"]
F = {name: i for i, name in enumerate(FEATURES)}
PRIOR_VIEWS = 50.0   # a product's rates are shrunk towards the store average until it has this many views


class Catalog:
    """Immutable snapshot of the products as arrays. Rebuilt (cheaply) when products or statistics change."""

    def __init__(self, pids: list[str], category: list[str], subcategory: list[str], brand: list[str],
                 price: np.ndarray, views: np.ndarray, carts: np.ndarray, purchases: np.ndarray,
                 exposure: np.ndarray | None = None,
                 names: tuple[list[str], list[str], list[str]] | None = None) -> None:
        self.pids = pids
        self.pos = {p: i for i, p in enumerate(pids)}
        # ids are append-only: a category/subcategory/brand keeps its id when the catalogue grows, so the
        # per-shopper counts keyed by subcategory id stay valid across snapshots
        prev = names or ([], [], [])
        self.cat_names = prev[0] + sorted(set(category) - set(prev[0]))
        self.sub_names = prev[1] + sorted(set(subcategory) - set(prev[1]))
        self.brand_names = prev[2] + sorted(set(brand) - set(prev[2]))
        cat_id = {c: i for i, c in enumerate(self.cat_names)}
        sub_id = {s: i for i, s in enumerate(self.sub_names)}
        brand_id = {b: i for i, b in enumerate(self.brand_names)}
        self.cat = np.array([cat_id[c] for c in category])
        self.sub = np.array([sub_id[s] for s in subcategory])
        self.brand = np.array([brand_id[b] for b in brand])
        self.sub_cat = np.zeros(len(self.sub_names), dtype=int)       # subcategory -> its category
        self.sub_cat[self.sub] = self.cat
        self.log_price = np.log(np.maximum(price, 0.5))
        self.by_cat = {c: np.flatnonzero(self.cat == c) for c in np.unique(self.cat)}
        self.by_sub = {s: np.flatnonzero(self.sub == s) for s in np.unique(self.sub)}

        # organic statistics. `exposure` is the number of store-wide purchases that happened while the
        # product existed: the same for all old products, smaller for a product added during the event,
        # so that a new product's share is not diluted by the months it was not there.
        n = len(pids)
        exposure = np.full(n, purchases.sum()) if exposure is None else exposure
        view_exposure = exposure * (views.sum() / max(purchases.sum(), 1.0))
        self.share = (purchases + 1.0) / (exposure + n)
        self.pop = np.log(self.share)
        self.view_share = np.log((views + 1.0) / (view_exposure + n))
        self.cart_rate = (carts + PRIOR_VIEWS * carts.sum() / max(views.sum(), 1.0)) / (views + PRIOR_VIEWS)
        self.buy_rate = (purchases + PRIOR_VIEWS * purchases.sum() / max(views.sum(), 1.0)) / (views + PRIOR_VIEWS)
        best_in_sub = np.zeros(len(self.sub_names))
        best_in_cat = np.zeros(len(self.cat_names))
        for k, members in self.by_sub.items():
            best_in_sub[k] = self.pop[members].max()
        for k, members in self.by_cat.items():
            best_in_cat[k] = self.pop[members].max()
        self.pop_vs_sub = self.pop - best_in_sub[self.sub]
        self.pop_vs_cat = self.pop - best_in_cat[self.cat]

        static = np.full((n, len(FEATURES)), np.nan, dtype=np.float32)
        for name in ("pop", "view_share", "cart_rate", "buy_rate", "log_price", "pop_vs_sub", "pop_vs_cat"):
            static[:, F[name]] = getattr(self, name)
        self.static = static


@dataclass(slots=True)
class Shopper:
    """Running totals for one shopper. `sub_*` are counts per subcategory id."""
    views: int = 0
    carts: int = 0
    purchases: int = 0
    sub_views: dict[int, int] = field(default_factory=dict)
    sub_purch: dict[int, int] = field(default_factory=dict)
    price_sum: float = 0.0            # sum of log prices of what they bought
    carted: dict[int, int] = field(default_factory=dict)   # product index -> ts, carted and not bought
    bought: set[int] = field(default_factory=set)          # product indices already bought

    def view(self, sub: int) -> None:
        self.views += 1
        self.sub_views[sub] = self.sub_views.get(sub, 0) + 1

    def cart(self, item: int, ts: int) -> None:
        self.carts += 1
        if item not in self.bought:
            self.carted[item] = ts

    def buy(self, item: int, sub: int, log_price: float) -> None:
        """An organic purchase: taste evidence, and the product is now satiated."""
        self.purchases += 1
        self.sub_purch[sub] = self.sub_purch.get(sub, 0) + 1
        self.price_sum += log_price
        self.bought.add(item)
        self.carted.pop(item, None)

    def sold(self, item: int) -> None:
        """A purchase through the carousel: satiated, but not counted as organic taste evidence."""
        self.bought.add(item)
        self.carted.pop(item, None)


NOBODY = Shopper()


def featurize(cat: Catalog, shopper: Shopper | None, page: int, device: int, region: int, recent: list[int],
              idx: np.ndarray, slot: np.ndarray | float = 1.0, is_live: float = 1.0) -> np.ndarray:
    """Feature matrix (len(idx) × len(FEATURES)) for the candidate products `idx` of one request.

    `recent` holds the product indices of recent_views, oldest first (unknown products dropped).
    """
    x = cat.static[idx].copy()
    x[:, F["page"]] = page
    x[:, F["device"]] = device
    x[:, F["region"]] = region
    x[:, F["slot"]] = slot
    x[:, F["is_live"]] = is_live
    x[:, F["n_recent"]] = len(recent)

    sub, catg = cat.sub[idx], cat.cat[idx]
    if recent:
        last = recent[-1]
        r = np.array(recent)
        x[:, F["same_cat"]] = catg == cat.cat[last]
        x[:, F["same_sub"]] = sub == cat.sub[last]
        x[:, F["same_brand"]] = cat.brand[idx] == cat.brand[last]
        x[:, F["in_recent"]] = np.isin(idx, r)
        x[:, F["is_last"]] = idx == last
        x[:, F["recent_sub_frac"]] = (sub[:, None] == cat.sub[r][None, :]).mean(axis=1)
        x[:, F["recent_cat_frac"]] = (catg[:, None] == cat.cat[r][None, :]).mean(axis=1)
        x[:, F["dprice_last"]] = cat.log_price[idx] - cat.log_price[last]
        x[:, F["dprice_recent"]] = cat.log_price[idx] - cat.log_price[r].mean()

    u = shopper or NOBODY
    x[:, F["u_views"]] = log(1 + u.views)
    x[:, F["u_purch"]] = log(1 + u.purchases)
    x[:, F["u_buy_rate"]] = (u.purchases + 2.5) / (u.views + 50.0)
    if u.views:
        sub_views = np.zeros(len(cat.sub_names))
        sub_views[list(u.sub_views)] = list(u.sub_views.values())
        cat_views = np.bincount(cat.sub_cat, weights=sub_views, minlength=len(cat.cat_names))
        x[:, F["u_sub_view"]] = sub_views[sub] / u.views
        x[:, F["u_cat_view"]] = cat_views[catg] / u.views
    if u.purchases:
        sub_purch = np.zeros(len(cat.sub_names))
        sub_purch[list(u.sub_purch)] = list(u.sub_purch.values())
        cat_purch = np.bincount(cat.sub_cat, weights=sub_purch, minlength=len(cat.cat_names))
        x[:, F["u_sub_purch"]] = sub_purch[sub] / u.purchases
        x[:, F["u_cat_purch"]] = cat_purch[catg] / u.purchases
        x[:, F["u_sub_purch_n"]] = np.log1p(sub_purch[sub])
        x[:, F["u_dprice"]] = cat.log_price[idx] - u.price_sum / u.purchases
    x[:, F["u_carted"]] = np.isin(idx, list(u.carted)) if u.carted else 0.0
    return x
