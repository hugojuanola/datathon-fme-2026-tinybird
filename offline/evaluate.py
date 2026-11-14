"""Offline validation of the ranking policy on the held-out last 7 days of shop.history_sessions.

    python -m offline.pull_data      # once: export the history to data/
    python -m offline.evaluate

Everything a policy may use (popularity, carts, purchases) is built only from events BEFORE the cut;
the policies are then asked to rank for the impressions AFTER it, running the same code as live
(reco.recommend). Two numbers per policy:

    hit@10      share of logged clicks / purchases whose product is in our top 10
    weighted    the same, weighting a hit by the attention its slot gets (slot 1 = 1, slot 10 = 0.15)

The live simulator has satiation (docs/findings.md) and the log does not, so the test set keeps only
clicks/purchases of products the shopper had NOT bought before: the cases that exist live.
The log only contains what the old system showed, so absolute values are pessimistic; the comparison
between policies is what matters.
"""
from __future__ import annotations

from collections import defaultdict

import numpy as np
import pandas as pd

from reco import recommend as policy
from reco.rawtree import ROOT
from reco.state import Product, State

DATA = ROOT / "data"
CUT = pd.Timestamp("2026-11-07").value // 10**6           # ms: train < cut <= test
SLOT_WEIGHT = np.array([21483, 12015, 8805, 6836, 5629, 5043, 4438, 3923, 3483, 3260]) / 21483  # clicks per slot in the log


def offline_state() -> State:
    """The State the live loop would have had at the cut, built from the local export."""
    state = State()
    for r in pd.read_parquet(DATA / "catalog.parquet").itertuples():
        state.products[r.product_id] = Product(r.category, r.subcategory, r.brand, r.price_eur, r.price_eur, False)
    ev = pd.read_parquet(DATA / "events.parquet", columns=["ts", "ev", "user_id", "product_id"])
    ev = ev[ev.ts < CUT // 1000]
    bought = ev[ev.ev == "p"]
    for u, p in zip(bought.user_id.values, bought.product_id.values):
        state.purchased[u].add(p)
    carts = ev[ev.ev == "a"]
    for u, p, t in zip(carts.user_id.values, carts.product_id.values, carts.ts.values):
        if p not in state.purchased[u]:
            state.carted[u][p] = int(t)
    counts = bought.product_id.value_counts()
    state.hist_pop = (counts / counts.sum()).to_dict()
    state._rank()
    return state


def test_set(state: State) -> pd.DataFrame:
    s = pd.read_parquet(DATA / "sessions.parquet", columns=["ts_ms", "user_id", "page", "rv", "clicked", "purchased"])
    s = s[(s.ts_ms >= CUT) & (s.clicked != "")].copy()
    s["rv"] = s.rv.map(lambda x: x.split(",") if x else [])
    fresh = [c not in state.purchased.get(u, ()) for u, c in zip(s.user_id.values, s.clicked.values)]
    return s[fresh]


def evaluate(name: str, recs: list[list[str]], test: pd.DataFrame) -> dict:
    rank = np.array([r.index(c) if c in r else -1 for r, c in zip(recs, test.clicked.values)])
    weight = np.where(rank >= 0, SLOT_WEIGHT[np.clip(rank, 0, 9)], 0.0)
    bought = (test.purchased != "").to_numpy()
    return {"policy": name,
            "click hit@10": (rank >= 0).mean(), "click weighted": weight.mean(),
            "purchase hit@10": (rank >= 0)[bought].mean(), "purchase weighted": weight[bought].mean()}


def main() -> None:
    state = offline_state()
    test = test_set(state)
    print(f"test: {len(test):,} clicks, {(test.purchased != '').sum():,} purchases after the cut "
          f"(products the shopper had not bought before)\n")
    baseline = [p for p in state.best][:10]
    rows = [evaluate("baseline (best sellers)", [baseline] * len(test), test)]

    def run(name: str, arm: str = "a", **lifts) -> None:
        saved = {k: getattr(policy, k) for k in lifts}
        for k, v in lifts.items():
            setattr(policy, k, v)
        recs = [policy.recommend(state, u, rv, arm)[0] for u, rv in zip(test.user_id.values, test.rv.values)]
        for k, v in saved.items():
            setattr(policy, k, v)
        rows.append(evaluate(name, recs, test))

    off = dict(LIFT_CATEGORY=1, LIFT_SUBCATEGORY=1, LIFT_CART=1, LIFT_CART_SAME=1)
    policy.ARMS.update({"1": 1.0, "2": 2.0, "3": 3.0, "5": 5.0})
    run("popularity, minus already bought", arm="1", **off)
    run("+ category of last view", arm="1", **{**off, "LIFT_CATEGORY": policy.LIFT_CATEGORY})
    run("+ subcategory", arm="1", LIFT_CART=1, LIFT_CART_SAME=1)
    run("+ abandoned carts", arm="1")
    policy.ARMS.update({"10": 10.0, "30": 30.0})
    for arm in ("2", "3", "5", "10", "30"):
        run(f"+ just viewed x{policy.ARMS[arm]:g}", arm=arm)
    for k in (1.5, 3, 5):
        run(f"  (cart in category x{k:g}, viewed x1)", arm="1", LIFT_CART_SAME=k)
    for k in (1.2, 2, 3):
        run(f"  (subcategory x{k:g}, viewed x1)", arm="1", LIFT_SUBCATEGORY=k)
    for k in (2, 8, 20):
        run(f"  (category x{k:g}, viewed x1)", arm="1", LIFT_CATEGORY=k)
    out = pd.DataFrame(rows).set_index("policy")
    print((100 * out).round(2).to_string())


if __name__ == "__main__":
    main()
