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
    "is_new_item", "item_age", "discount", "attr_prior", "attr_a", "attr_b",
    # how it matches this session
    "page", "n_recent", "same_cat", "same_sub", "same_brand", "in_recent", "is_last",
    "recent_sub_frac", "recent_cat_frac", "dprice_last", "dprice_recent", "recent_new", "recent_attr",
    "recent_attr_max", "recent_attr_mean",
    # how it matches this shopper
    "u_views", "u_purch", "u_buy_rate", "u_cat_view", "u_cat_purch", "u_sub_view", "u_sub_purch",
    "u_sub_purch_n", "u_sub_rank", "u_sub_bought_frac", "u_sub_cart", "u_cat_cart", "u_brand_purch", "u_brand_purch_n", "u_attr_p", "u_attr_p_lo", "u_attr_c", "u_attr_c_lo", "u_attr_v", "u_attr_v_lo",
    "u_bought_n",
    "u_carted", "u_cart_age", "u_n_carted", "u_dprice",
    # context
    "device", "region", "slot",
]
CATEGORICAL = ["page", "device", "region", "attr_a", "attr_b"]
F = {name: i for i, name in enumerate(FEATURES)}
PRIOR_VIEWS = 50.0   # a product's rates are shrunk towards the store average until it has this many views
ATTR_PRIOR = 5.0     # a shopper's taste for an attribute is shrunk towards everybody's until they have this many purchases

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
              idx: np.ndarray, now: float, slot: np.ndarray | float = 1.0) -> np.ndarray:
    """Feature matrix (len(idx) × len(FEATURES)) for the candidate products `idx` of one request.

    `recent` holds the product indices of recent_views, oldest first (unknown products dropped);
    `now` is the time of the request in unix seconds.
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
