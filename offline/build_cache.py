"""Build the start-up cache of the live server: every shopper's state at the end of the 60-day history.

    python -m offline.pull_data        # once
    python -m offline.build_cache      # → $SKORE_DATA_DIR/cache/history.pkl (≈1 min, no RawTree queries)

The history never changes, so the server loads this file instead of asking RawTree to aggregate 12 M
events at every start (which takes minutes and slows down whatever else is querying). It is produced by
the same replay that builds the training set, so the server starts from exactly the state the model
was trained on. Without the file the server falls back to the SQL aggregates (reco/state.py).
"""
from __future__ import annotations

import pickle
import time

import numpy as np
import pandas as pd

from offline.build_dataset import DATA, load_catalogs, replay
from reco.features import Shopper
from reco.priority import background


def main() -> None:
    background()   # never compete with the live loop for the CPU
    t0 = time.time()
    cat, _ = load_catalogs()
    events = pd.read_parquet(DATA / "events.parquet", columns=["ts", "ev", "user_id", "product_id"])
    sold = pd.read_parquet(DATA / "sessions.parquet", columns=["ts_ms", "user_id", "device", "region", "page", "rv",
                                                               "shown", "clicked", "purchased"])
    sold = sold[sold.purchased != ""]          # what the old carousel sold: satiated too
    shoppers: dict[str, Shopper] = {}
    replay(cat, shoppers, events, sold, np.zeros(len(sold), bool), 0.0, [])
    counts = events.groupby(["product_id", "ev"]).size().unstack(fill_value=0)
    cache = {"pids": cat.pids[:5000], "cat_names": cat.cat_names, "sub_names": cat.sub_names,
             "brand_names": cat.brand_names, "shoppers": shoppers,
             "counts": {p: (float(r.get("v", 0)), float(r.get("a", 0)), float(r.get("p", 0))) for p, r in counts.iterrows()}}
    path = DATA / "cache" / "history.pkl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(cache, f, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"{path}: {len(shoppers):,} shoppers, {len(cache['counts']):,} products in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
