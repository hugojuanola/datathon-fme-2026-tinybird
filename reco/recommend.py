"""The ranking policies: 10 products for one shopper.

Every request is answered best-first (slot 1 gets ~6× the attention of slot 10). Two hard rules sit
outside any model:

    never show a product that is out of stock       (one would invalidate the whole answer)
    never show a product the shopper already bought (satiation: live, they are almost never bought again)

    rules   score = popularity × measured lifts, for every product in the catalogue. Transparent, no
            training: the control arm, the fallback, and the first stage of the model policy.
    explore the model's best 20 products, 10 of them at random, in random order. A small share of the
            traffic: it shows the model what happens when it is NOT obeyed, which is the only unbiased
            way to check it (and the next model) — a model that only ever sees the outcome of its own
            choices cannot find its own mistakes. On during practice, off during the final.
    model   two stages, the standard shape of an industrial recommender:
              1. retrieve  the 500 best products by the rules (0.1 ms)
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

from reco.features import DEVICES, F, FEATURES, PAGES, REGIONS, Catalog, Shopper, featurize
from reco.state import State

# lifts of the rules policy: each is a measured ratio of purchase rates (docs/findings.md)
LIFT_CATEGORY = 5.0      # same category as the last view            (live: 0.27 % vs 0.052 % per impression)
LIFT_SUBCATEGORY = 1.4   # same subcategory as the last view         (log:  0.21 % vs 0.13 %)
LIFT_CART = 10.0         # carted, never bought, other category      (live: 0.53 % vs 0.052 %)
LIFT_CART_SAME = 2.2     # carted, never bought, session's category  (live: 0.58 % vs 0.27 %)
LIFT_VIEWED = 3.0        # in this session's recent views            (live A/B: ×3 beat ×1.5, ×10 and ×30)
LIFT_BOUGHT_SUB = 5.0    # retrieval only: the shopper bought in that subcategory before (live: 5.6× with
LIFT_BOUGHT_SUB_3 = 10.0 # 1-2 purchases, 14× with 3+). The model decides how much it is really worth.
CANDIDATES = 500         # products handed from the rules to the model
EXPLORE_POOL = 20        # the exploration arm samples its 10 products from the model's best 20


class Ranker:
    """The two LightGBM models, loaded from models/."""

    def __init__(self, folder: Path) -> None:
        import lightgbm as lgb

        self.click = lgb.Booster(model_file=str(folder / "click.txt"))
        self.conv = lgb.Booster(model_file=str(folder / "conv.txt"))
        if self.click.feature_name() != FEATURES:
            raise ValueError("models/click.txt was trained with a different feature list: retrain")
        self.conv_columns = [F[name] for name in self.conv.feature_name()]

    def score(self, x: np.ndarray) -> np.ndarray:
        return self.click.predict(x, num_threads=2) * self.conv.predict(x[:, self.conv_columns], num_threads=2)


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
    if retrieval and shopper and shopper.sub_purch:
        for sub, n in list(shopper.sub_purch.items()):
            if sub in cat.by_sub:
                score[cat.by_sub[sub]] *= LIFT_BOUGHT_SUB_3 if n >= 3 else LIFT_BOUGHT_SUB
    return score


def recommend(state: State, ranker: Ranker | None, req: dict, policy: str,
              candidates: int | None = None) -> tuple[list[str], list[str]]:
    """(10 product ids, why each is there) for a request {user, rv, page, device, region}.

    why: v = just viewed · c = abandoned cart · b = the shopper bought in that subcategory before ·
         s = subcategory of the last view · k = its category · g = none of those
    """
    cat = state.catalog
    shopper = state.shoppers.get(req["user"])
    recent = [cat.pos[p] for p in req["rv"] if p in cat.pos]
    score = score_rules(cat, shopper, recent, retrieval=policy != "rules")
    n = len(score)
    blocked = [i for i in list(shopper.bought) if i < n] if shopper else []
    blocked += [cat.pos[p] for p in list(state.unavailable) if p in cat.pos]
    score[blocked] = -1.0

    if policy != "rules":
        k = min(candidates or CANDIDATES, n - len(set(blocked)))
        top = np.argpartition(-score, k - 1)[:k]
        x = featurize(cat, shopper, PAGES.get(req["page"], 2), DEVICES.get(req["device"], 0),
                      REGIONS.get(req["region"], -1), recent, top, slot=1.0, is_live=1.0)
        order = np.argsort(-ranker.score(x), kind="stable")
        if policy == "explore":     # reproducible: the same request always gets the same sample
            rng = np.random.default_rng(zlib.crc32(req.get("id", "").encode()))
            order = rng.permutation(order[:EXPLORE_POOL])
        top = top[order[:10]]
    else:
        top = np.argpartition(-score, 10)[:10]
        top = top[np.argsort(-score[top], kind="stable")]

    last = recent[-1] if recent else None
    carted = shopper.carted if shopper else {}
    bought_subs = shopper.sub_purch if shopper else {}
    why = []
    for i in top:
        why.append("v" if i in recent else "c" if i in carted else "b" if cat.sub[i] in bought_subs
                   else "g" if last is None else "s" if cat.sub[i] == cat.sub[last]
                   else "k" if cat.cat[i] == cat.cat[last] else "g")
    return [cat.pids[i] for i in top], why


def safe_list(state: State) -> list[str]:
    """Last resort: the in-stock best sellers (what the organisers' fallback would show)."""
    return [p for p in state.best if p not in state.unavailable][:10]


def is_valid(state: State, items: list[str]) -> bool:
    return (len(items) == 10 and len(set(items)) == 10
            and all(p in state.products and p not in state.unavailable for p in items))
