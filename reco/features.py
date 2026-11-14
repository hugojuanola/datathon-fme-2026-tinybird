"""One definition of every model feature, used to build the training set AND to serve live.

Training/serving skew is the classic way a recommender that looks good offline fails live, so there is
exactly one `featurize()` and both paths call it. No feature is a product id or a user id: everything is
a count, a rate, a share or a match, so the model transfers to shoppers and products it has never seen.

    Catalog     the products as arrays, plus their organic statistics (popularity, cart rate…)
    Shopper     what one shopper has done so far (updated event by event)
    featurize   (catalog, shopper, request, candidate products) → feature matrix
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from math import log, log1p

import numpy as np

PAGES = {"home": 0, "category": 1, "product": 2}
DEVICES = {"web": 0, "ios": 1, "android": 2}
REGIONS = {r: i for i, r in enumerate(["Andalucía", "Aragón", "Canarias", "Castilla y León", "Catalunya",
                                       "Comunitat Valenciana", "Galicia", "Madrid", "Murcia", "País Vasco"])}

FEATURES = [
    # the product itself
    "pop", "view_share", "cart_rate", "buy_rate", "log_price", "pop_vs_sub", "pop_vs_cat",
    "is_new_item", "item_age", "discount", "trend", "attr_prior", "attr_a", "attr_b",
    # how it matches this session
    "page", "n_recent", "same_cat", "same_sub", "same_brand", "in_recent", "is_last",
    "recent_sub_frac", "recent_cat_frac", "dprice_last", "dprice_recent", "recent_new", "recent_attr",
    "recent_attr_max", "recent_attr_mean",
    # how it matches this shopper
    "u_views", "u_purch", "u_buy_rate", "u_cat_view", "u_cat_purch", "u_sub_view", "u_sub_purch",
    "u_sub_purch_n", "u_sub_rank", "u_sub_bought_frac", "rank_left", "pop_vs_left", "u_sub_cart", "u_cat_cart", "u_brand_purch", "u_brand_purch_n", "u_attr_p", "u_attr_p_lo", "u_attr_c", "u_attr_c_lo", "u_attr_v", "u_attr_v_lo",
    "u_bought_n",
    "u_carted", "u_cart_age", "u_n_carted", "u_dprice",
    # context
    "device", "region", "slot",
]
CATEGORICAL = ["page", "device", "region", "attr_a", "attr_b"]
F = {name: i for i, name in enumerate(FEATURES)}
PRIOR_VIEWS = 50.0   # a product's rates are shrunk towards the store average until it has this many views
ATTR_PRIOR = 5.0     # a shopper's taste for an attribute is shrunk towards everybody's until they have this many purchases

# Trends: a group of products that suddenly sells several times its usual share of the store's organic
# purchases. Measured on 14 Nov (python -m offline.store_moves): one subcategory at a time, for 45 minutes,
# purchases x8-12 and views x3-4, every product in it rising alike. The detector reads the organic stream:
#   views say WHEN   - 20x more numerous than purchases, so a trend shows within about a minute and its end
#                      within two;
#   purchases say HOW MUCH - starting from what the views imply (purchases rise like views ** 1.8) and
#                      moving to the measured ratio as purchases accumulate.
# The same statistic watches subcategories, categories and brands; a product takes the largest lift among
# its groups. Every count is shrunk towards "as usual", so a small group needs real evidence.
LEVELS = ("subcategory", "category", "brand")
LEVEL_SIZE = 100_000     # a group's key is level * LEVEL_SIZE + its id
VIEW_WINDOW = 2          # minutes of views a trend is detected from (plus the minute in progress)
VIEW_PRIOR = 20.0        # pseudo-views pulling the ratio towards 1
VIEW_GATE = 2.0          # trending = viewed at least this many times its usual share…
VIEW_MIN = 40            # …with at least this many views in the window
VIEW_TO_BUY = 1.8        # purchases rise like views ** this (four trends: views x3.0-4.2, purchases x7.8-11.9)
BUY_WINDOW = 5           # minutes of purchases the size of a trend is measured on
BUY_PRIOR = 3.0          # pseudo-purchases, at the ratio the views imply (or at 1 when views say nothing)
BUY_GATE = 4.0           # purchases alone also count as a trend: this many times the usual share…
BUY_MIN = 12             # …with this many purchases, and still selling in the last VIEW_WINDOW minutes.
                         # (2.5 / 8 fired on noise: purchases come in baskets. Replayed every second on
                         # 14 Nov: 174 s of false alarms in 9.5 h with 2.5 / 8, 19 s with 4 / 12.)
TREND_CAP = 12.0


class Trends:
    """Organic views and purchases per minute and group → which groups are trending right now, and how much."""

    def __init__(self) -> None:
        self.views: dict[int, dict[int, int]] = {}     # minute -> group key -> views
        self.buys: dict[int, dict[int, int]] = {}      # minute -> group key -> purchases
        self.newest = 0                                # the minute in progress

    def add(self, minute: int, keys: tuple[int, ...], bought: bool) -> None:
        table = self.buys if bought else self.views
        counts = table.get(minute)
        if counts is None:
            counts = table[minute] = {}
        for key in keys:
            counts[key] = counts.get(key, 0) + 1
        if minute > self.newest:
            self.newest = minute

    def _window(self, table: dict[int, dict[int, int]], minutes: int) -> dict[int, int]:
        total: dict[int, int] = {}
        for minute in range(self.newest - minutes, self.newest + 1):
            for key, n in list(table.get(minute, {}).items()):
                total[key] = total.get(key, 0) + n
        return total

    def lifts(self, usual_views: dict[int, float], usual_buys: dict[int, float]) -> dict[int, float]:
        """{group key: how many times its usual share of the purchases it sells now}, trending groups only.

        usual_*: each group's usual share of the store's views / purchases (see usual_shares).
        """
        seen, sold = self._window(self.views, VIEW_WINDOW), self._window(self.buys, BUY_WINDOW)
        sold_now = self._window(self.buys, VIEW_WINDOW)
        n_levels = len(LEVELS)
        out: dict[int, float] = {}
        # every event is counted once per level, so the store totals are the sums divided by the levels
        n_seen, n_sold, n_sold_now = (sum(t.values()) / n_levels for t in (seen, sold, sold_now))
        for key in set(seen) | set(sold):
            share_v, share_b = usual_views.get(key), usual_buys.get(key)
            if not share_v or not share_b:
                continue
            v, b, b_now = seen.get(key, 0), sold.get(key, 0), sold_now.get(key, 0)
            view_lift = (v + VIEW_PRIOR) / (n_seen * share_v + VIEW_PRIOR)
            if v >= VIEW_MIN and view_lift >= VIEW_GATE:
                implied = view_lift ** VIEW_TO_BUY
                lift = max((b + BUY_PRIOR * implied) / (n_sold * share_b + BUY_PRIOR), view_lift)
            else:
                lift = (b + BUY_PRIOR) / (n_sold * share_b + BUY_PRIOR)
                still = b_now >= 3 and (b_now + 1.0) / (n_sold_now * share_b + 1.0) >= 2.0
                if not (b >= BUY_MIN and lift >= BUY_GATE and still):
                    continue
            out[key] = float(min(lift, TREND_CAP))
        # a trending subcategory drags its category and its brands up with it: when subcategories explain
        # the move, they are the answer; the wider levels speak only when no subcategory does
        return {k: v for k, v in out.items() if k < LEVEL_SIZE} or out

    def forget(self, minutes: int = 30) -> None:
        for table in (self.views, self.buys):
            for minute in [m for m in list(table) if m < self.newest - minutes]:
                table.pop(minute, None)


def group_keys(cat: "Catalog") -> list[tuple[int, ...]]:
    """For every product, the keys of the groups it belongs to (one per level of LEVELS)."""
    return list(zip(cat.sub.tolist(), (LEVEL_SIZE + cat.cat).tolist(), (2 * LEVEL_SIZE + cat.brand).tolist()))


def usual_shares(cat: "Catalog") -> tuple[dict[int, float], dict[int, float]]:
    """Each group's usual share of the store's views and purchases, {group key: share}."""
    out = []
    for counts in (cat.views_n, cat.purchases_n):
        shares: dict[int, float] = {}
        total = max(float(counts.sum()), 1.0)
        for level, ids in enumerate((cat.sub, cat.cat, cat.brand)):
            for i, n in enumerate(np.bincount(ids, weights=counts)):
                shares[level * LEVEL_SIZE + i] = n / total
        out.append(shares)
    return out[0], out[1]


def trend_vector(cat: "Catalog", lifts: dict[int, float]) -> np.ndarray | None:
    """Per product, the largest lift among its trending groups (1 = nothing special); None when nothing trends."""
    if not lifts:
        return None
    vector = np.ones(len(cat.pids))
    for key, lift in lifts.items():
        level, i = divmod(key, LEVEL_SIZE)
        members = (cat.sub, cat.cat, cat.brand)[level] == i
        vector[members] = np.maximum(vector[members], lift)
    return vector


def trend_names(cat: "Catalog", lifts: dict[int, float]) -> dict[str, float]:
    """The trending groups by name, for logs: {"Bike Helmets": 8.4, "brand Tinove": 3.1}."""
    out = {}
    for key, lift in lifts.items():
        level, i = divmod(key, LEVEL_SIZE)
        names = (cat.sub_names, cat.cat_names, cat.brand_names)[level]
        name = names[i] if i < len(names) else str(i)
        out[name if level == 0 else f"{LEVELS[level]} {name}"] = round(lift, 1)
    return out

# Every description names two attributes of the product ("organic ingredients", "a luxury feel", "designed
# for kids"…). Shoppers buy by attribute: within a subcategory, the attributes of what a shopper bought
# before pick the product they buy next with AUC 0.68 (docs/findings.md). And a description is all a new
# product has. Two of the four description templates name the attributes unambiguously; the vocabulary is
# taken from those and then looked up in every description.
_REVEALING = (re.compile(r"\): (.+), (.+)\.\s*$"), re.compile(r"featuring (.+)\. Comes with (.+)\.\s*$"))
_ARTICLE = re.compile(r"^(a|an|the)\s+", re.IGNORECASE)


def attribute_phrases(descriptions: list[str]) -> set[str]:
    found: set[str] = set()
    for text in descriptions:
        for pattern in _REVEALING:
            match = pattern.search(text)
            if match:
                found.update(_ARTICLE.sub("", g.strip()).lower() for g in match.groups())
    return found


class Catalog:
    """Immutable snapshot of the products as arrays. Rebuilt (cheaply) when products or statistics change."""

    def __init__(self, pids: list[str], category: list[str], subcategory: list[str], brand: list[str],
                 price: np.ndarray, views: np.ndarray, carts: np.ndarray, purchases: np.ndarray,
                 exposure: np.ndarray | None = None,
                 names: tuple | None = None,
                 base_price: np.ndarray | None = None, added: np.ndarray | None = None,
                 description: list[str] | None = None) -> None:
        self.pids = pids
        self.pos = {p: i for i, p in enumerate(pids)}
        # ids are append-only: a category/subcategory/brand keeps its id when the catalogue grows, so the
        # per-shopper counts keyed by subcategory id stay valid across snapshots
        prev = [list(names[k]) if names and len(names) > k else [] for k in range(4)]
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
        self.sub_size = np.maximum(np.bincount(self.sub, minlength=len(self.sub_names)), 1)
        self.log_price = np.log(np.maximum(price, 0.5))
        self.by_cat = {c: np.flatnonzero(self.cat == c) for c in np.unique(self.cat)}
        self.by_sub = {s: np.flatnonzero(self.sub == s) for s in np.unique(self.sub)}
        n = len(pids)
        # attributes named in the description: attr[i, k] = 1 if product i has attribute k
        self.attr_names = prev[3] + sorted(attribute_phrases(description or []) - set(prev[3]))
        self.names = (self.cat_names, self.sub_names, self.brand_names, self.attr_names)
        self.attr = np.zeros((n, len(self.attr_names)), dtype=np.float32)
        for i, text in enumerate(description or []):
            low = text.lower()
            for k, phrase in enumerate(self.attr_names):
                if phrase in low:
                    self.attr[i, k] = 1.0
        self.attr_n = self.attr.sum(axis=1)
        self.attr_ids = [tuple(np.flatnonzero(row).tolist()) for row in self.attr]
        # the product's attributes as two categorical features (lower id first): lets the model learn what an
        # attribute is worth by itself and for a kind of shopper (device, region) — all a new shopper offers
        self.attr_a = np.array([t[0] if t else np.nan for t in self.attr_ids], dtype=float)
        self.attr_b = np.array([t[1] if len(t) > 1 else np.nan for t in self.attr_ids], dtype=float)
        # added: unix seconds when the product was added during the event (0 = original catalogue)
        self.added = np.zeros(n) if added is None else np.asarray(added, dtype=float)
        self.is_new = self.added > 0
        # discount: log(price now / price at the start of the stream); 0 = unchanged, -0.22 = 20 % off
        self.discount = self.log_price - (self.log_price if base_price is None else np.log(np.maximum(base_price, 0.5)))

        # organic statistics. `exposure` is the number of store-wide purchases that happened while the
        # product existed: the same for all old products, smaller for a product added during the event,
        # so that a new product's share is not diluted by the months it was not there.
        exposure = np.full(n, purchases.sum()) if exposure is None else exposure
        self.views_n, self.purchases_n = np.asarray(views, dtype=float), np.asarray(purchases, dtype=float)
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
        # inside its subcategory: 0 = the best seller, and the popularities in that order (for "what is left")
        self.rank_in_sub = np.zeros(n, dtype=int)
        self.sub_pop_sorted: dict[int, np.ndarray] = {}
        for k, members in self.by_sub.items():
            order = np.argsort(-self.pop[members], kind="stable")
            self.rank_in_sub[members[order]] = np.arange(len(members))
            self.sub_pop_sorted[int(k)] = self.pop[members[order]]
        self.is_new_item = self.is_new.astype(float)
        # attr_share: share of all purchases that are of a product with the attribute (what "everybody" likes);
        # attr_prior: how well products with this product's attributes sell on average (log lift over the
        # average product): the only popularity hint a brand-new product has
        total = max(float(purchases.sum()), 1.0)
        self.attr_share = (self.attr.T @ purchases + 1.0) / (total + 1.0)
        per_product = (self.attr.T @ purchases + 1.0) / np.maximum(self.attr.sum(axis=0), 1.0)
        self.attr_prior = (self.attr @ np.log(per_product / (total / n))) / np.maximum(self.attr_n, 1.0)

        static = np.full((n, len(FEATURES)), np.nan, dtype=np.float32)
        for name in ("pop", "view_share", "cart_rate", "buy_rate", "log_price", "pop_vs_sub", "pop_vs_cat",
                     "is_new_item", "discount", "attr_prior", "attr_a", "attr_b"):
            static[:, F[name]] = getattr(self, name)
        self.static = static


@dataclass(slots=True)
class Shopper:
    """Running totals for one shopper. `sub_*` are keyed by subcategory id."""
    views: int = 0
    carts: int = 0
    purchases: int = 0
    sub_views: dict[int, int] = field(default_factory=dict)
    sub_purch: dict[int, int] = field(default_factory=dict)
    sub_bought: dict[int, int] = field(default_factory=dict)   # distinct products bought per subcategory
    sub_carts: dict[int, int] = field(default_factory=dict)    # carts per subcategory
    brand_purch: dict[int, int] = field(default_factory=dict)  # purchases per brand id
    attr_purch: dict[int, int] = field(default_factory=dict)   # purchases per description attribute id
    attr_cart: dict[int, int] = field(default_factory=dict)    # carts per attribute id
    attr_view: dict[int, int] = field(default_factory=dict)    # views per attribute id
    price_sum: float = 0.0            # sum of log prices of what they bought
    carted: dict[int, int] = field(default_factory=dict)   # product index -> ts (s), carted and not bought
    bought: set[int] = field(default_factory=set)          # product indices already bought

    def view(self, sub: int, attrs: tuple = ()) -> None:
        self.views += 1
        self.sub_views[sub] = self.sub_views.get(sub, 0) + 1
        for a in attrs:
            self.attr_view[a] = self.attr_view.get(a, 0) + 1

    def cart(self, item: int, ts: int, attrs: tuple = (), sub: int = -1) -> None:
        self.carts += 1
        if sub >= 0:
            self.sub_carts[sub] = self.sub_carts.get(sub, 0) + 1
        for a in attrs:
            self.attr_cart[a] = self.attr_cart.get(a, 0) + 1
        if item not in self.bought:
            self.carted[item] = ts

    def buy(self, item: int, sub: int, log_price: float, attrs: tuple = (), brand: int = -1) -> None:
        """An organic purchase: taste evidence, and the product is now satiated."""
        self.purchases += 1
        self.sub_purch[sub] = self.sub_purch.get(sub, 0) + 1
        if brand >= 0:
            self.brand_purch[brand] = self.brand_purch.get(brand, 0) + 1
        for a in attrs:
            self.attr_purch[a] = self.attr_purch.get(a, 0) + 1
        self.price_sum += log_price
        self.sold(item, sub)

    def sold(self, item: int, sub: int) -> None:
        """The product is satiated (bought organically or through a carousel)."""
        if item not in self.bought:
            self.bought.add(item)
            self.sub_bought[sub] = self.sub_bought.get(sub, 0) + 1
        self.carted.pop(item, None)


NOBODY = Shopper()


def featurize(cat: Catalog, shopper: Shopper | None, page: int, device: int, region: int, recent: list[int],
              idx: np.ndarray, now: float, slot: np.ndarray | float = 1.0,
              trend: np.ndarray | None = None) -> np.ndarray:
    """Feature matrix (len(idx) × len(FEATURES)) for the candidate products `idx` of one request.

    `recent` holds the product indices of recent_views, oldest first (unknown products dropped);
    `now` is the time of the request in unix seconds; `trend` is trend_vector() at that moment.
    """
    x = cat.static[idx].copy()
    x[:, F["page"]] = page
    x[:, F["device"]] = device
    x[:, F["region"]] = region
    x[:, F["slot"]] = slot
    x[:, F["n_recent"]] = len(recent)
    added = cat.added[idx]
    fresh = added > 0
    if fresh.any():
        x[fresh, F["item_age"]] = np.log1p(np.maximum(now - added[fresh], 0.0) / 3600.0)

    sub, catg = cat.sub[idx], cat.cat[idx]
    # log of how many times its usual share the product's group (subcategory, category or brand) sells now
    x[:, F["trend"]] = np.log(trend[idx]) if trend is not None and len(trend) == len(cat.pids) else 0.0
    attrs, n_attrs = cat.attr[idx], cat.attr_n[idx]
    described = n_attrs > 0
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
        x[:, F["recent_new"]] = float(cat.is_new[r].any())
        if described.any():     # share of the product's attributes that the last viewed product has too…
            x[described, F["recent_attr"]] = (attrs[described] @ cat.attr[last]) / n_attrs[described]
            shared = (attrs[described] @ cat.attr[r].T) / n_attrs[described][:, None]     # …and each recent view
            x[described, F["recent_attr_max"]] = shared.max(axis=1)
            x[described, F["recent_attr_mean"]] = shared.mean(axis=1)

    u = shopper or NOBODY
    n_sub = len(cat.sub_names)
    x[:, F["u_views"]] = log(1 + u.views)
    x[:, F["u_purch"]] = log(1 + u.purchases)
    x[:, F["u_buy_rate"]] = (u.purchases + 2.5) / (u.views + 50.0)
    x[:, F["u_bought_n"]] = log(1 + len(u.bought))
    # what is left of the subcategory for this shopper: how many better sellers they have not bought yet, and
    # the product's popularity against the best of those (a shopper never buys the same product twice)
    ranks = cat.rank_in_sub[idx]
    x[:, F["rank_left"]] = np.log1p(ranks)
    x[:, F["pop_vs_left"]] = cat.pop_vs_sub[idx]
    if u.bought:
        mine = np.fromiter(u.bought, dtype=int)
        mine = mine[mine < len(cat.sub)]
        mine_sub, mine_rank = cat.sub[mine], cat.rank_in_sub[mine]
        for s in np.unique(mine_sub).tolist():
            rows = np.flatnonzero(sub == s)
            if len(rows):
                taken = np.sort(mine_rank[mine_sub == s])
                free = int(np.argmax(taken != np.arange(len(taken)))) if (taken != np.arange(len(taken))).any() else len(taken)
                pops = cat.sub_pop_sorted[s]
                x[rows, F["rank_left"]] = np.log1p(ranks[rows] - np.searchsorted(taken, ranks[rows]))
                x[rows, F["pop_vs_left"]] = cat.pop[idx[rows]] - pops[min(free, len(pops) - 1)]
    if u.views:
        seen = dict(u.sub_views)        # copies: another thread updates the shopper while we read
        sub_views = np.zeros(n_sub)
        sub_views[list(seen)] = list(seen.values())
        cat_views = np.bincount(cat.sub_cat, weights=sub_views, minlength=len(cat.cat_names))
        x[:, F["u_sub_view"]] = sub_views[sub] / u.views
        x[:, F["u_cat_view"]] = cat_views[catg] / u.views
    if u.purchases:
        purch = dict(u.sub_purch)
        subs, counts = np.array(list(purch)), np.array(list(purch.values()), dtype=float)
        sub_purch = np.zeros(n_sub)
        sub_purch[subs] = counts
        cat_purch = np.bincount(cat.sub_cat, weights=sub_purch, minlength=len(cat.cat_names))
        total = counts.sum()
        x[:, F["u_sub_purch"]] = sub_purch[sub] / total
        x[:, F["u_cat_purch"]] = cat_purch[catg] / total
        x[:, F["u_sub_purch_n"]] = np.log1p(sub_purch[sub])
        x[:, F["u_dprice"]] = cat.log_price[idx] - u.price_sum / u.purchases
        rank = np.full(n_sub, np.nan)   # 1 = the subcategory this shopper buys most from
        rank[subs[np.argsort(-counts, kind="stable")]] = np.arange(1, len(subs) + 1)
        x[:, F["u_sub_rank"]] = rank[sub]
        brands = {b: c for b, c in dict(u.brand_purch).items() if b < len(cat.brand_names)}
        if brands:
            brand_purch = np.zeros(len(cat.brand_names))
            brand_purch[list(brands)] = list(brands.values())
            x[:, F["u_brand_purch"]] = brand_purch[cat.brand[idx]] / total
            x[:, F["u_brand_purch_n"]] = np.log1p(brand_purch[cat.brand[idx]])
    if u.carts:
        in_cart = {s: c for s, c in dict(u.sub_carts).items() if s < n_sub}
        if in_cart:
            sub_carts = np.zeros(n_sub)
            sub_carts[list(in_cart)] = list(in_cart.values())
            cat_carts = np.bincount(cat.sub_cat, weights=sub_carts, minlength=len(cat.cat_names))
            x[:, F["u_sub_cart"]] = sub_carts[sub] / u.carts
            x[:, F["u_cat_cart"]] = cat_carts[catg] / u.carts
    if u.sub_bought:
        owned = dict(u.sub_bought)
        sub_owned = np.zeros(n_sub)
        sub_owned[list(owned)] = list(owned.values())
        x[:, F["u_sub_bought_frac"]] = sub_owned[sub] / cat.sub_size[sub]
    if described.any():
        # Attribute taste, read from three kinds of evidence (purchases, carts, views): how much more than
        # everybody this shopper goes for the product's attributes (1 = like everybody). For each: the
        # average over the product's attributes, and the worse of them ("lo": do they like both?).
        for tag, evidence, n_events in (("p", u.attr_purch, u.purchases), ("c", u.attr_cart, u.carts), ("v", u.attr_view, u.views)):
            tastes = {a: c for a, c in dict(evidence).items() if a < attrs.shape[1]}
            if tastes:
                seen_attr = np.zeros(attrs.shape[1])
                seen_attr[list(tastes)] = list(tastes.values())
                lift = (seen_attr + ATTR_PRIOR * cat.attr_share) / (n_events + ATTR_PRIOR) / cat.attr_share
                x[described, F[f"u_attr_{tag}"]] = ((attrs @ lift) / np.maximum(n_attrs, 1))[described]
                x[described, F[f"u_attr_{tag}_lo"]] = np.where(attrs > 0, lift, np.inf).min(axis=1)[described]
    carted = dict(u.carted)
    x[:, F["u_n_carted"]] = log(1 + len(carted))
    x[:, F["u_carted"]] = 0.0
    if carted:
        for row in np.flatnonzero(np.isin(idx, list(carted))):
            x[row, F["u_carted"]] = 1.0
            x[row, F["u_cart_age"]] = log1p(max(now - carted.get(int(idx[row]), now), 0.0) / 60.0)
    return x
