"""Offline validation of the ranking policies on the held-out last 7 days of shop.history_sessions.

    python -m offline.pull_data      # once
    python -m offline.train          # the models are fitted on the days BEFORE the cut
    python -m offline.evaluate

The store is replayed up to the cut (same code as the training set and the live server), then every policy
ranks the whole catalogue for the requests AFTER it, through `reco.recommend` — the code that runs live.

    hit@10      share of logged clicks / purchases whose product is in our top 10
    weighted    the same, weighting a hit by the attention its slot gets (slot 1 = 1, slot 10 = 0.15)

Two things the log cannot tell, and live feedback has to:
  - it only contains what the old system showed (same category as the last view, popular products), so a
    cross-category recommendation can never score here, however good it is live;
  - it has no satiation, so the test set keeps only clicks on products the shopper had NOT bought before:
    the cases that exist live.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from offline.build_dataset import load_catalogs, replay
from reco.features import Shopper
from reco.priority import background
from reco.rawtree import DATA, ROOT
from reco.recommend import Ranker, recommend
from reco.state import Product, State

CUT = pd.Timestamp("2026-11-07").value // 10**6           # ms: state < cut <= test (same cut as offline/train.py)
SLOT_WEIGHT = np.array([21483, 12015, 8805, 6836, 5629, 5043, 4438, 3923, 3483, 3260]) / 21483  # clicks per slot in the log


def state_at_cut() -> State:
    """The State the live server would have had at the cut."""
    cat, _ = load_catalogs()
    events = pd.read_parquet(DATA / "events.parquet", columns=["ts", "ev", "user_id", "product_id"])
    events = events[events.ts < CUT // 1000]
    sold = pd.read_parquet(DATA / "sessions.parquet", columns=["ts_ms", "user_id", "device", "region", "page", "rv",
                                                               "shown", "clicked", "purchased"])
    sold = sold[(sold.purchased != "") & (sold.ts_ms < CUT)]
    state = State()
    base = pd.read_parquet(DATA / "catalog.parquet")
    for r in base.itertuples():
        state._add_product(r.product_id, Product(r.category, r.subcategory, r.brand, r.price_eur))
    replay(cat, state.shoppers, events, sold, np.zeros(len(sold), bool), 0.0, [])
    counts = events.groupby(["product_id", "ev"]).size().unstack(fill_value=0)
    state.hist_counts = {p: (float(r.get("v", 0)), float(r.get("a", 0)), float(r.get("p", 0))) for p, r in counts.iterrows()}
    state._snapshot((cat.cat_names, cat.sub_names, cat.brand_names))
    return state


def test_set(state: State) -> pd.DataFrame:
    s = pd.read_parquet(DATA / "sessions.parquet",
                        columns=["ts_ms", "user_id", "device", "region", "page", "rv", "clicked", "purchased"])
    s = s[(s.ts_ms >= CUT) & (s.clicked != "")].copy()
    nobody = Shopper()
    fresh = [state.pos[c] not in state.shoppers.get(u, nobody).bought for u, c in zip(s.user_id.values, s.clicked.values)]
    return s[fresh]


def evaluate(name: str, recs: list[list[str]], test: pd.DataFrame) -> dict:
    rank = np.array([r.index(c) if c in r else -1 for r, c in zip(recs, test.clicked.values)])
    weight = np.where(rank >= 0, SLOT_WEIGHT[np.clip(rank, 0, 9)], 0.0)
    out = {"policy": name}
    for label, mask in (("all", np.ones(len(test), bool)), ("home", (test.page == "home").to_numpy())):
        bought = (test.purchased != "").to_numpy() & mask
        out[f"{label}: click hit@10"] = (rank >= 0)[mask].mean()
        out[f"{label}: purchase hit@10"] = (rank >= 0)[bought].mean()
        out[f"{label}: purchase weighted"] = weight[bought].mean()
    return out


def main() -> None:
    background()   # never compete with the live loop for the CPU
    state = state_at_cut()
    test = test_set(state)
    ranker = Ranker(ROOT / "models")
    print(f"test: {len(test):,} clicks, {(test.purchased != '').sum():,} purchases after the cut "
          f"(products the shopper had not bought before); {(test.page == 'home').mean():.1%} on the home page\n")
    requests = [{"user": r.user_id, "rv": r.rv.split(",") if r.rv else [], "page": r.page, "device": r.device,
                 "region": r.region} for r in test.itertuples()]
    best = state.best[:10]
    rows = [evaluate("baseline (best sellers)", [best] * len(test), test)]
    rows.append(evaluate("rules (v4)", [recommend(state, None, r, "rules")[0] for r in requests], test))
    rows.append(evaluate("model (v5): rules retrieve, model ranks", [recommend(state, ranker, r, "model")[0] for r in requests], test))
    print((100 * pd.DataFrame(rows).set_index("policy")).round(1).to_string())


if __name__ == "__main__":
    main()
