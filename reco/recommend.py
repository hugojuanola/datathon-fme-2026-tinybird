"""The ranking policies: 10 products for one shopper.

Every request is answered best-first (slot 1 gets ~6× the attention of slot 10). Two hard rules sit
outside any model:

    never show a product that is out of stock       (one would invalidate the whole answer)
    never show a product the shopper already bought (satiation: live, they are almost never bought again)

    rules   score = popularity × measured lifts, for every product in the catalogue. Transparent, no
            training: the control arm, the fallback, and the first stage of the model policy.
    explore the model's list, slightly shuffled: its best 4 products in random order in slots 1-4, then
            6 of its next 10 at random. A small share of the traffic: it shows what happens when the
            model is NOT obeyed, which is the only unbiased way to check it (and the next model) — a
            model that only ever sees the outcome of its own choices cannot find its own mistakes.
            Shuffling only near the top keeps it cheap: the first version (10 random products out of
            the best 20) converted 0.83 % against 1.94 % for the model. Practice round only.
    model   two stages, the standard shape of an industrial recommender:
              1. retrieve  the 1,000 best products by the rules (0.2 ms)
              2. rank      them by P(click) × P(purchase | click), two gradient-boosted models over the
                           features of reco/features.py (the product, how it matches the session, how it
                           matches the shopper)
            Ranking 500 candidates instead of 5,100 products is 10× faster and gives the same top 10 in
            almost every request (measured: see docs/findings.md).
"""
from __future__ import annotations

import zlib
from pathlib import Path

import numpy as np

from reco.features import ATTR_PRIOR, DEVICES, F, FEATURES, PAGES, REGIONS, Catalog, Shopper, featurize
from reco.state import State

# lifts of the rules policy: each is a measured ratio of purchase rates (docs/findings.md)
LIFT_CATEGORY = 5.0      # same category as the last view            (live: 0.27 % vs 0.052 % per impression)
LIFT_SUBCATEGORY = 1.4   # same subcategory as the last view         (log:  0.21 % vs 0.13 %)
LIFT_CART = 10.0         # carted, never bought, other category      (live: 0.53 % vs 0.052 %)
LIFT_CART_SAME = 2.2     # carted, never bought, session's category  (live: 0.58 % vs 0.27 %)
LIFT_VIEWED = 3.0        # in this session's recent views            (live A/B: ×3 beat ×1.5, ×10 and ×30)
LIFT_BOUGHT_SUB = 5.0    # retrieval only: the shopper bought in that subcategory before (live: 5.6× with
LIFT_BOUGHT_SUB_3 = 10.0 # 1-2 purchases, 14× with 3+). The model decides how much it is really worth.
CANDIDATES = 1000        # products handed from the rules to the model
LIFT_SHARED_ATTR = (1.0, 2.0, 4.5)   # retrieval only: 0 / 1 / 2 description attributes shared with the last
                                     # viewed product (live, slot-adjusted: 0.75 / 1.7 / 4.3 of the average)
ORGANIC_TOP = 300        # candidates (the best by the carousel models) the organic model is asked about
NEIGHBOURS = 10          # a trending product takes the organic factor of this many products ranked just above
                         # and just below it
EXPLORE_HEAD = 4         # exploration: the model's best 4 are shown in slots 1-4, in random order
EXPLORE_POOL = 14        # …and slots 5-10 are 6 products drawn at random from its ranks 5-14


class Ranker:
    """One trained ranker: the two LightGBM models of models/<name>/, and a third one if it is there.

    click.txt × conv.txt = P(click) × P(purchase | click), learned from what carousels showed (offline/train.py).
    organic.txt (optional) = "this shopper is about to buy this product in the store", learned from what
    shoppers bought after a request whoever showed it (offline/organic.py); see propensity().
    Each model file lists the features it was trained on, so rankers trained on different feature sets
    can run side by side in an A/B: every one picks its own columns out of the same feature matrix.
    """
    CONSTANTS = {"is_live": 1.0}   # features older models expect and newer feature sets dropped

    def __init__(self, folder: Path, click_only: bool = False) -> None:
        import lightgbm as lgb

        self.name = folder.name
        self.click_only = click_only      # rank by P(click) alone: an A/B arm, to see what the second model adds
        self.click = lgb.Booster(model_file=str(folder / "click.txt"))
        self.conv = self.click if click_only else lgb.Booster(model_file=str(folder / "conv.txt"))
        extra = [n for n in self.CONSTANTS if n in self.click.feature_name() + self.conv.feature_name()]
        self.extra = np.array([self.CONSTANTS[n] for n in extra], dtype=np.float32)
        where = {**F, **{n: len(FEATURES) + i for i, n in enumerate(extra)}}
        missing = [n for n in self.click.feature_name() + self.conv.feature_name() if n not in where]
        if missing:
            raise ValueError(f"{folder}: trained with features this code does not compute: {sorted(set(missing))}")
        self.click_columns = [where[n] for n in self.click.feature_name()]
        self.conv_columns = [where[n] for n in self.conv.feature_name()]
        self.organic = lgb.Booster(model_file=str(folder / "organic.txt")) if (folder / "organic.txt").exists() else None
        self.organic_columns = [F[n] for n in self.organic.feature_name()] if self.organic else []

    def score(self, x: np.ndarray) -> np.ndarray:
        if len(self.extra):
            x = np.hstack([x, np.broadcast_to(self.extra, (len(x), len(self.extra)))])
        clicks = self.click.predict(x[:, self.click_columns], num_threads=2)
        return clicks if self.click_only else clicks * self.conv.predict(x[:, self.conv_columns], num_threads=2)

    def propensity(self, x: np.ndarray) -> np.ndarray | None:
        """How likely the shopper is to buy each product in the store soon; None if this ranker has no such model."""
        return self.organic.predict(x[:, self.organic_columns], num_threads=2) if self.organic else None


def score_rules(cat: Catalog, shopper: Shopper | None, recent: list[int], retrieval: bool = False) -> np.ndarray:
    score = cat.share.copy()
    last = recent[-1] if recent else None
    if last is not None:
        score[cat.by_cat[cat.cat[last]]] *= LIFT_CATEGORY
        score[cat.by_sub[cat.sub[last]]] *= LIFT_SUBCATEGORY
    if shopper and shopper.carted:
        for i in list(shopper.carted):
            if i < len(score):
                same = last is not None and cat.cat[i] == cat.cat[last]
                score[i] *= LIFT_CART_SAME if same else LIFT_CART
    if recent:
        score[list(set(recent))] *= LIFT_VIEWED
    if retrieval and last is not None and cat.attr.shape[1]:
        score *= np.take(LIFT_SHARED_ATTR, np.minimum(cat.attr @ cat.attr[last], 2).astype(int))
    if retrieval and shopper and shopper.sub_purch:
        for sub, n in list(shopper.sub_purch.items()):
            if sub in cat.by_sub:
                score[cat.by_sub[sub]] *= LIFT_BOUGHT_SUB_3 if n >= 3 else LIFT_BOUGHT_SUB
    if retrieval and shopper and cat.attr.shape[1]:
        # products whose description attributes the shopper goes for (purchases and carts count fully,
        # views a quarter): works from the first few events of a brand-new shopper
        seen_attr, events = np.zeros(cat.attr.shape[1]), 0.0
        for evidence, n_events, weight in ((shopper.attr_purch, shopper.purchases, 1.0), (shopper.attr_cart, shopper.carts, 1.0),
                                           (shopper.attr_view, shopper.views, 0.25)):
            for a, c in dict(evidence).items():
                if a < len(seen_attr):
                    seen_attr[a] += weight * c
            events += weight * n_events
        if events > 0:
            lift = (seen_attr + ATTR_PRIOR * cat.attr_share) / (events + ATTR_PRIOR) / cat.attr_share
            score *= np.where(cat.attr_n > 0, np.clip((cat.attr @ lift) / np.maximum(cat.attr_n, 1), 0.5, 3.0), 1.0)
    return score


def level_trending(want: np.ndarray, p: np.ndarray, trending: np.ndarray) -> np.ndarray:
    """The organic factors `want` of some candidates, with those of the trending products replaced by the
    median factor of the products the ranker scores about as high (NEIGHBOURS just above and just below,
    among the ones that are not trending).

    The organic model learned which product a shopper goes on to buy among the candidates of an ordinary
    day. A product that is a candidate only because its subcategory is trending is one it was never asked
    about, and its answer means nothing: on 14 Nov (Face Cream, 21:30 UTC) the arms with the organic factor
    put 1.7 products of the trending subcategory in every list where the carousel models alone put 0.1, and
    1,600 such impressions brought 1 click. So on those products the organic model has no say: they keep
    the place the carousel models and the trend give them."""
    plain = np.flatnonzero(~trending)
    if not len(plain):
        return want
    plain = plain[np.argsort(-p[plain], kind="stable")]     # the others, best first
    place = np.searchsorted(-p[plain], -p[trending])         # where each trending product falls among them
    out = want.copy()
    for i, k in zip(np.flatnonzero(trending), place):
        out[i] = np.median(want[plain[max(k - NEIGHBOURS, 0):k + NEIGHBOURS]])
    return out


def new_shopper(req: dict) -> bool:
    """The request says so (is_new_user): a shopper the 60-day history knows nothing about."""
    return str(req.get("is_new")).lower() in ("true", "1")


def recommend(state: State, ranker: Ranker | None, req: dict, policy: str, candidates: int | None = None,
              trend: float | str = 0.0, price: float = 0.0, organic: float = 0.0, fresh: float = 1.0,
              pool: int | None = None, trend_lift: np.ndarray | None = None) -> tuple[list[str], list[str]]:
    """(10 product ids, why each is there) for a request {user, rv, page, device, region}.

    The store moves, and the organic stream shows by how much before our own feedback can:
    trend: what to do with a live trend. 0 = ignore it. A number = products of a group selling L times its
           usual share right now (state.trend_lift; `trend_lift` overrides it, for tests) have their scores
           multiplied by L ** trend. "model" = no multiplier: the ranker gets the trend as a feature.
    price: price elasticity. A product at r times its catalogue price has its score multiplied by r ** -price
           (measured on 14 Nov: a 19 % drop sells x1.3-1.45, an elasticity of about 1.6).
    organic: how much to listen to what shoppers go on to buy in the store: the ranker's score is multiplied by
           its organic propensity ** organic (0 = carousel models alone; needs organic.txt in the ranker).
    pool: how many of the carousel models' best candidates the organic factor is applied to (ORGANIC_TOP if
           not given). 10 = the carousel models pick the ten and the organic factor only orders them: no
           product enters the list on the organic model's word. That is exactly what was measured on held-out
           lists (14 Nov, 38,627 lists, position-based estimate): +2.5 % to +4.7 % purchases, depending on
           how fast attention falls down the list (findings §22).
    fresh: a product added during the event has its score multiplied by this when the shopper is a known one
           (1 = nothing). Measured on 14 Nov on 30,000 lists the ranker had not seen: after a click, a known
           shopper buys such a product 37 % of the time, against 25 % for the original catalogue; the ranker,
           trained when few of them had been sold, expected 26 % (observed / predicted purchases 1.37 against
           0.90). New shoppers buy both alike, and the ranker knows it.
    why: v = just viewed · c = abandoned cart · t = trending subcategory · b = the shopper bought in that
         subcategory before · s = subcategory of the last view · k = its category · g = none of those
    """
    cat = state.catalog
    shopper = state.shoppers.get(req["user"])
    recent = [cat.pos[p] for p in req["rv"] if p in cat.pos]
    score = score_rules(cat, shopper, recent, retrieval=policy != "rules")
    n = len(score)
    lift, hot = None, None      # lift: every store move together · hot: the trending products
    by_model = trend == "model"
    power = 0.0 if by_model else float(trend)
    trend_lift = state.trend_lift if trend_lift is None else trend_lift
    if trend_lift is not None and len(trend_lift) != n:     # computed on another snapshot of the catalogue
        trend_lift = None
    try:
        if price and cat.discount.any():
            lift = np.clip(np.exp(-price * cat.discount), 0.5, 2.5)
        if power and trend_lift is not None:
            hot = trend_lift > 1
            lift = trend_lift ** power if lift is None else lift * trend_lift ** power
        if lift is not None:
            score *= lift
    except Exception as e:     # a store move is a bonus: never let it cost an answer
        print(f"store-move lift failed: {str(e)[:200]}", flush=True)
        lift, hot = None, None
    blocked = [i for i in list(shopper.bought) if i < n] if shopper else []
    blocked += [cat.pos[p] for p in list(state.unavailable) if p in cat.pos]
    score[blocked] = -1.0

    if policy != "rules":
        k = min(candidates or CANDIDATES, n - len(set(blocked)))
        top = np.argpartition(-score, k - 1)[:k]
        x = featurize(cat, shopper, PAGES.get(req["page"], 2), DEVICES.get(req["device"], 0),
                      REGIONS.get(req["region"], -1), recent, top, int(req["ts_ms"]) / 1000, slot=1.0,
                      trend=trend_lift if by_model else None)
        p = ranker.score(x)
        if lift is not None:
            p = p * lift[top]
        if fresh != 1.0 and not new_shopper(req):
            p = np.where(cat.is_new[top], p * fresh, p)
        if organic and ranker.organic is not None:
            # the organic model is the slow one (1,500 trees), and beyond the best few hundred candidates it
            # cannot change the first 10: on 250 requests, applying it to the best 200 gave the same lists
            n_best = pool or ORGANIC_TOP
            best = np.argpartition(-p, n_best - 1)[:n_best] if len(p) > n_best else np.arange(len(p))
            want = ranker.propensity(x[best]) ** organic
            if hot is not None and hot[top[best]].any():
                want = level_trending(want, p[best], hot[top[best]])
            blended = np.zeros(len(p))
            blended[best] = p[best] * want
            p = blended
        order = np.argsort(-p, kind="stable")
        if policy == "explore":     # reproducible: the same request always gets the same sample
            rng = np.random.default_rng(zlib.crc32(req.get("id", "").encode()))
            order = np.concatenate([rng.permutation(order[:EXPLORE_HEAD]),
                                    rng.permutation(order[EXPLORE_HEAD:EXPLORE_POOL])])
        top = top[order[:10]]
    else:
        top = np.argpartition(-score, 10)[:10]
        top = top[np.argsort(-score[top], kind="stable")]

    last = recent[-1] if recent else None
    carted = shopper.carted if shopper else {}
    bought_subs = shopper.sub_purch if shopper else {}
    why = []
    for i in top:
        why.append("v" if i in recent else "c" if i in carted else "t" if hot is not None and hot[i]
                   else "b" if cat.sub[i] in bought_subs
                   else "g" if last is None else "s" if cat.sub[i] == cat.sub[last]
                   else "k" if cat.cat[i] == cat.cat[last] else "g")
    return [cat.pids[i] for i in top], why


def safe_list(state: State) -> list[str]:
    """Last resort: the in-stock best sellers (what the organisers' fallback would show)."""
    return [p for p in state.best if p not in state.unavailable][:10]


def is_valid(state: State, items: list[str]) -> bool:
    return (len(items) == 10 and len(set(items)) == 10
            and all(p in state.products and p not in state.unavailable for p in items))
