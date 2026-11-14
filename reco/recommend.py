"""The ranking policy: 10 products for one shopper.

It scores every product in the catalogue and takes the top 10:

    score = popularity × lift(category) × lift(subcategory) × lift(just viewed) × lift(abandoned cart)

- popularity   share of purchases, all-time + live window (new products only have the live part)
- category     same category as the last product viewed
- subcategory  same subcategory as the last product viewed
- just viewed  the product is in this session's recent_views
- cart         the shopper carted it and never bought it (a smaller lift if the product is already
               boosted by the session's category: the two effects overlap rather than multiply)
- already bought by this shopper, or out of stock → score 0, never shown

Why multiply: v1 ranked by tier (viewed > carted > popular) and the feedback showed that an obscure
product does not sell just because it was viewed. The lifts act on top of how attractive the product
is to begin with. Each lift is a measured ratio of purchase rates (docs/findings.md).
"""
from __future__ import annotations

import zlib

import numpy as np

from reco.state import State

LIFT_CATEGORY = 5.0      # live: 0.27 % vs 0.052 % per impression (same vs other category)
LIFT_SUBCATEGORY = 1.4   # log:  0.21 % vs 0.13 %
LIFT_CART = 10.0         # live: 0.53 % vs 0.052 % (carted vs not, product outside the session's category)
LIFT_CART_SAME = 2.2     # live: 0.58 % vs 0.27 % (carted vs not, product already in the session's category)
ARMS = {"a": 3.0, "b": 1.5}     # lift of a just-viewed product. Live A/B so far: ×3 (2.6 %) > ×10 (0.9 %) > ×30; the log says 2-3×


def arm_of(request_id: str) -> str:
    """Deterministic A/B split on the request id, so both variants see the same kind of traffic."""
    return "ab"[zlib.crc32(request_id.encode()) % 2]


def recommend(state: State, user: str, recent_views: list[str], arm: str) -> tuple[list[str], list[str]]:
    """Return (10 product ids, why each one is there: v=viewed c=carted s=subcategory k=category g=global)."""
    ix = state.index
    score = ix.pop.copy()
    why = np.full(len(score), "g", dtype=object)

    last = next((state.products[p] for p in reversed(recent_views) if p in state.products), None)
    if last:
        members = ix.by_cat[last.category]
        score[members] *= LIFT_CATEGORY
        why[members] = "k"
        members = ix.by_sub[last.subcategory]
        score[members] *= LIFT_SUBCATEGORY
        why[members] = "s"

    carted = state.carted.get(user)
    if carted:
        for p in list(carted):
            i = ix.pos.get(p)
            if i is not None:
                same = last is not None and state.products[p].category == last.category
                score[i] *= LIFT_CART_SAME if same else LIFT_CART
                why[i] = "c"

    viewed = [ix.pos[p] for p in set(recent_views) if p in ix.pos]
    if viewed:
        score[viewed] *= ARMS[arm]
        why[viewed] = "v"

    blocked = [ix.pos[p] for p in list(state.purchased.get(user, ())) if p in ix.pos]
    blocked += [ix.pos[p] for p in list(state.unavailable) if p in ix.pos]
    score[blocked] = -1.0

    top = np.argpartition(-score, 10)[:10]
    top = top[np.argsort(-score[top], kind="stable")]
    return [ix.pids[i] for i in top], [why[i] for i in top]


def safe_list(state: State) -> list[str]:
    """Last resort: the in-stock best sellers (what the organisers' fallback would show)."""
    return [p for p in state.best if p not in state.unavailable][:10]


def is_valid(state: State, items: list[str]) -> bool:
    return (len(items) == 10 and len(set(items)) == 10
            and all(p in state.products and p not in state.unavailable for p in items))
