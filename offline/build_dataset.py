"""Build the training table: one row per (request, product shown), with features as known AT THAT MOMENT.

    python -m offline.pull_data            # once
    python -m offline.pull_data live       # refresh the live part
    python -m offline.build_dataset        # → data/train.parquet

It replays the store in time order — 12 M organic events interleaved with the carousel requests — keeping
one `Shopper` per user up to date, and calls the same `featurize()` the live loop uses. A request's
features therefore never see the future (no leakage), and offline == online by construction.

Two sources of rows:
    log    shop.history_sessions: what the old carousel showed (all clicked requests + a sample of the rest)
    live   team_NN.feedback: what the fallback and our own versions showed, with the real simulator's outcome
"""
from __future__ import annotations

import time

import numpy as np
import pandas as pd

from reco.features import DEVICES, FEATURES, PAGES, REGIONS, Catalog, Shopper, featurize
from reco.rawtree import DATA, ROOT
from reco.priority import background

KEEP_UNCLICKED = 0.12     # share of requests without a click that are kept (weighted back by 1 / this)


def load_catalogs() -> tuple[Catalog, Catalog]:
    """(catalog as of the history, catalog as of the live stream): same products, same order."""
    base = pd.read_parquet(DATA / "catalog.parquet")
    updates = pd.read_parquet(DATA / "catalog_updates.parquet")
    new = updates[updates.change == "new_product"].drop_duplicates("product_id")
    products = pd.concat([base, new[base.columns.intersection(new.columns)]], ignore_index=True)
    added = dict(zip(new.product_id, new.ts_ms // 1000))
    pids = products.product_id.tolist()

    def counts(events: pd.DataFrame) -> np.ndarray:
        table = events.groupby(["product_id", "ev"]).size().unstack(fill_value=0).reindex(pids).fillna(0)
        return np.stack([table.get(k, pd.Series(0, index=table.index)).to_numpy(float) for k in "vap"])

    hist = pd.read_parquet(DATA / "events.parquet", columns=["ev", "product_id"])
    h = counts(hist)
    args = (pids, products.category.tolist(), products.subcategory.tolist(), products.brand.tolist())
    cat_hist = Catalog(*args, products.price_eur.to_numpy(float), *h)

    live = pd.read_parquet(DATA / "live_events.parquet", columns=["ts", "ev", "product_id"])
    l = counts(live)
    buys = np.sort(live.ts[live.ev == "p"].to_numpy())
    exposure = np.full(len(pids), h[2].sum() + len(buys), dtype=float)
    for p, t in added.items():      # a new product has only been exposed to the purchases since it appeared
        exposure[pids.index(p)] = len(buys) - np.searchsorted(buys, t)
    price = products.price_eur.to_numpy(float).copy()
    latest = updates.sort_values("ts_ms").drop_duplicates("product_id", keep="last")
    pos = {p: i for i, p in enumerate(pids)}
    for p, v in zip(latest.product_id, latest.price_eur):
        price[pos[p]] = v
    cat_live = Catalog(*args, price, *(h + l), exposure=exposure,
                       names=(cat_hist.cat_names, cat_hist.sub_names, cat_hist.brand_names))
    return cat_hist, cat_live


def replay(cat: Catalog, shoppers: dict[str, Shopper], events: pd.DataFrame, requests: pd.DataFrame,
           keep: np.ndarray, is_live: float, out: list) -> None:
    """Apply `events` in time order; for each kept request emit the feature rows of its 10 shown products."""
    pos, sub_of, log_price = cat.pos, cat.sub.tolist(), cat.log_price.tolist()
    ev_ts = events.ts.tolist()
    ev_type = events.ev.tolist()
    ev_user = [shoppers.setdefault(u, Shopper()) for u in events.user_id.tolist()]
    ev_item = [pos.get(p, -1) for p in events.product_id.tolist()]
    slots = np.arange(1, 11, dtype=np.float32)
    j, n_ev = 0, len(ev_ts)

    def apply_until(t: float) -> None:
        nonlocal j
        while j < n_ev and ev_ts[j] <= t:
            u, item, kind = ev_user[j], ev_item[j], ev_type[j]
            if item >= 0:
                if kind == "v":
                    u.view(sub_of[item])
                elif kind == "a":
                    u.cart(item, ev_ts[j])
                else:
                    u.buy(item, sub_of[item], log_price[item])
            j += 1

    for i, r in enumerate(requests.itertuples(index=False)):
        apply_until(r.ts_ms // 1000)
        shopper = shoppers.get(r.user_id)
        if shopper is None:
            shopper = shoppers[r.user_id] = Shopper()
        shown = [pos.get(p, -1) for p in r.shown.split(",")]
        if keep[i] and len(shown) == 10 and min(shown) >= 0:
            idx = np.array(shown)
            recent = [pos[p] for p in r.rv.split(",") if p in pos] if r.rv else []
            x = featurize(cat, shopper, PAGES[r.page], DEVICES[r.device], REGIONS[r.region], recent, idx, slots, is_live)
            clicked = pos.get(r.clicked, -2)
            bought = pos.get(r.purchased, -2)
            out.append((x, idx == clicked, idx == bought, np.array([k in shopper.bought for k in shown]), i, r.ts_ms))
        if r.purchased:
            item = pos.get(r.purchased, -1)
            if item >= 0:
                shopper.sold(item)
    apply_until(float("inf"))     # the events after the last request


def assemble(out: list, weight: np.ndarray, source: str, extra: dict | None = None) -> pd.DataFrame:
    df = pd.DataFrame(np.concatenate([o[0] for o in out]), columns=FEATURES)
    df["click"] = np.concatenate([o[1] for o in out])
    df["buy"] = np.concatenate([o[2] for o in out])
    df["bought_before"] = np.concatenate([o[3] for o in out])
    rows = np.repeat([o[4] for o in out], 10)
    df["request"] = rows
    df["ts_ms"] = np.repeat([o[5] for o in out], 10)
    df["weight"] = weight[rows].astype(np.float32)
    df["source"] = source
    for name, values in (extra or {}).items():
        df[name] = values[rows]
    return df


def main() -> None:
    background()   # never compete with the live loop for the CPU
    t0 = time.time()
    cat_hist, cat_live = load_catalogs()
    shoppers: dict[str, Shopper] = {}
    rng = np.random.default_rng(0)

    sessions = pd.read_parquet(DATA / "sessions.parquet",
                               columns=["ts_ms", "user_id", "device", "region", "page", "rv", "shown", "clicked", "purchased"])
    clicked = (sessions.clicked != "").to_numpy()
    keep = clicked | (rng.random(len(sessions)) < KEEP_UNCLICKED)
    weight = np.where(clicked, 1.0, 1.0 / KEEP_UNCLICKED)
    events = pd.read_parquet(DATA / "events.parquet", columns=["ts", "ev", "user_id", "product_id"])
    out: list = []
    replay(cat_hist, shoppers, events, sessions, keep, 0.0, out)
    log = assemble(out, weight, "log")
    print(f"log: {len(log):,} rows from {keep.sum():,} requests in {time.time() - t0:.0f}s", flush=True)
    del events, sessions, out

    feedback = pd.read_parquet(DATA / "live_feedback.parquet").sort_values("ts_ms").reset_index(drop=True)
    live_events = pd.read_parquet(DATA / "live_events.parquet", columns=["ts", "ev", "user_id", "product_id"])
    out = []
    replay(cat_live, shoppers, live_events, feedback, np.ones(len(feedback), bool), 1.0, out)
    live = assemble(out, np.ones(len(feedback)), "live",
                    {"served_by": feedback.served_by.to_numpy(), "is_new": feedback.is_new.to_numpy()})
    print(f"live: {len(live):,} rows from {len(feedback):,} requests", flush=True)

    table = pd.concat([log, live], ignore_index=True)
    table.to_parquet(DATA / "train.parquet", index=False)
    print(f"data/train.parquet: {len(table):,} rows × {len(FEATURES)} features in {time.time() - t0:.0f}s", flush=True)
    print(table.groupby("source")[["click", "buy", "bought_before"]].mean().round(5).to_string())


if __name__ == "__main__":
    main()
