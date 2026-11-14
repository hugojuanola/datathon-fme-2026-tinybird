"""Build the training table: one row per (request, product shown), with features as known AT THAT MOMENT.

    python -m offline.pull_data            # once
    python -m offline.build_dataset log    # once (5 min): → train_log.parquet
    python -m offline.pull_data live       # refresh our live feedback
    python -m offline.build_dataset live   # every retrain (seconds): → train_live.parquet

It replays the store in time order — 12 M organic events interleaved with the carousel requests — keeping
one `Shopper` per user up to date, and calls the same `featurize()` the live loop uses. A request's
features therefore never see the future (no leakage), and offline == online by construction.

Two sources of rows:
    log    shop.history_sessions: what the old carousel showed (all clicked requests + a sample of the rest)
    live   team_NN.feedback: what the fallback and our own versions showed, with the real simulator's outcome
"""
from __future__ import annotations

import json
import pickle
import sys
import time

import numpy as np
import pandas as pd

from reco.features import DEVICES, FEATURES, PAGES, REGIONS, Catalog, Shopper, featurize
from reco.rawtree import DATA, ROOT
from reco.priority import background

KEEP_UNCLICKED = 0.12     # share of requests without a click that are kept (weighted back by 1 / this)


def load_catalogs(fresh_names: bool = False) -> tuple[Catalog, Catalog]:
    """(catalog as of the history, catalog as of the live stream): same products, same order.

    Category / subcategory / brand / attribute ids must be the ones the start-up cache was built with (the
    cached shoppers are keyed by them): they are read from cache/names.json unless `fresh_names`.
    """
    base = pd.read_parquet(DATA / "catalog.parquet")
    names_file = DATA / "cache" / "names.json"
    if not fresh_names and names_file.exists():
        names = tuple(json.loads(names_file.read_text(encoding="utf-8")))
    else:       # ids from the original catalogue only; anything a later product brings is appended after them
        zero = np.zeros(len(base))
        names = Catalog(base.product_id.tolist(), base.category.tolist(), base.subcategory.tolist(), base.brand.tolist(),
                        base.price_eur.to_numpy(float), zero, zero, zero, description=base.description.tolist()).names
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
    text = products.description.fillna("").tolist()
    cat_hist = Catalog(*args, products.price_eur.to_numpy(float), *h, names=names, description=text)

    live = live_events()
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
    added_at = np.array([added.get(p, 0) for p in pids], dtype=float)
    cat_live = Catalog(*args, price, *(h + l), exposure=exposure,
                       names=cat_hist.names, base_price=products.price_eur.to_numpy(float), added=added_at,
                       description=text)
    return cat_hist, cat_live


def live_events() -> pd.DataFrame:
    """The live stream so far (ts in seconds, ev, user_id, product_id), in time order: from the server's own
    journal when this machine runs it (no RawTree query at all), else from the export."""
    segments = sorted((DATA / "cache" / "journal").glob("events-*.tsv"), key=lambda p: int(p.stem.split("-")[1]))
    if not segments:
        return pd.read_parquet(DATA / "live_events.parquet", columns=["ts", "ev", "user_id", "product_id"])
    parts = [pd.read_csv(p, sep=chr(9), names=["t", "ev", "user_id", "product_id"], quoting=3,
                         on_bad_lines="skip", dtype=str) for p in segments]
    ev = pd.concat(parts, ignore_index=True).dropna()
    ev = ev[ev.t.str.isdigit()].drop_duplicates()        # segments of overlapping runs repeat events
    ev["ts"] = ev.t.astype("int64") // 1000
    ev = ev.sort_values("ts", kind="stable")
    return ev[["ts", "ev", "user_id", "product_id"]].reset_index(drop=True)


def live_feedback() -> pd.DataFrame:
    parts = [pd.read_parquet(p) for p in sorted((DATA / "live").glob("feedback-*.parquet"))]
    df = pd.concat([p for p in parts if len(p)], ignore_index=True)
    return df.drop_duplicates("request_id").sort_values("ts_ms").reset_index(drop=True)


def replay(cat: Catalog, shoppers: dict[str, Shopper], events: pd.DataFrame, requests: pd.DataFrame,
           keep: np.ndarray, out: list) -> None:
    """Apply `events` in time order; for each kept request emit the feature rows of its 10 shown products."""
    pos, sub_of, log_price, brand_of = cat.pos, cat.sub.tolist(), cat.log_price.tolist(), cat.brand.tolist()
    attrs_of = cat.attr_ids
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
                    u.view(sub_of[item], attrs_of[item])
                elif kind == "a":
                    u.cart(item, ev_ts[j], attrs_of[item], sub_of[item])
                else:
                    u.buy(item, sub_of[item], log_price[item], attrs_of[item], brand_of[item])
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
            x = featurize(cat, shopper, PAGES[r.page], DEVICES[r.device], REGIONS[r.region], recent, idx,
                          r.ts_ms / 1000, slots)
            clicked = pos.get(r.clicked, -2)
            bought = pos.get(r.purchased, -2)
            out.append((x, idx == clicked, idx == bought, np.array([k in shopper.bought for k in shown]), i, r.ts_ms, idx))
        if r.purchased:
            item = pos.get(r.purchased, -1)
            if item >= 0:
                shopper.sold(item, sub_of[item])
    apply_until(float("inf"))     # the events after the last request


def assemble(out: list, weight: np.ndarray, source: str, extra: dict | None = None) -> pd.DataFrame:
    df = pd.DataFrame(np.concatenate([o[0] for o in out]), columns=FEATURES)
    df["click"] = np.concatenate([o[1] for o in out])
    df["buy"] = np.concatenate([o[2] for o in out])
    df["bought_before"] = np.concatenate([o[3] for o in out])
    df["item"] = np.concatenate([o[6] for o in out]).astype(np.int32)     # product index: for analysis, never a feature
    rows = np.repeat([o[4] for o in out], 10)
    df["request"] = rows
    df["ts_ms"] = np.repeat([o[5] for o in out], 10)
    df["weight"] = weight[rows].astype(np.float32)
    df["source"] = source
    for name, values in (extra or {}).items():
        df[name] = values[rows]
    return df


def build_log(cat: Catalog) -> dict[str, Shopper]:
    """The old carousel's log → train_log.parquet. Returns every shopper's state at the end of the history."""
    t0 = time.time()
    shoppers: dict[str, Shopper] = {}
    rng = np.random.default_rng(0)
    sessions = pd.read_parquet(DATA / "sessions.parquet",
                               columns=["ts_ms", "user_id", "device", "region", "page", "rv", "shown", "clicked", "purchased"])
    clicked = (sessions.clicked != "").to_numpy()
    keep = clicked | (rng.random(len(sessions)) < KEEP_UNCLICKED)
    weight = np.where(clicked, 1.0, 1.0 / KEEP_UNCLICKED)
    events = pd.read_parquet(DATA / "events.parquet", columns=["ts", "ev", "user_id", "product_id"])
    out: list = []
    replay(cat, shoppers, events, sessions, keep, out)
    log = assemble(out, weight, "log")
    log.to_parquet(DATA / "train_log.parquet", index=False)
    print(f"train_log.parquet: {len(log):,} rows from {keep.sum():,} requests in {time.time() - t0:.0f}s", flush=True)
    return shoppers


def build_live(cat: Catalog, shoppers: dict[str, Shopper]) -> None:
    """Our live feedback → train_live.parquet, continuing from the shoppers' state at the end of the history."""
    t0 = time.time()
    feedback = live_feedback()
    out: list = []
    replay(cat, shoppers, live_events(), feedback, np.ones(len(feedback), bool), out)
    live = assemble(out, np.ones(len(feedback)), "live",
                    {"served_by": feedback.served_by.to_numpy(), "is_new": feedback.is_new.to_numpy()})
    live.to_parquet(DATA / "train_live.parquet", index=False)
    print(f"train_live.parquet: {len(live):,} rows from {len(feedback):,} requests in {time.time() - t0:.0f}s", flush=True)


def main() -> None:
    background()   # never compete with the live loop for the CPU
    what = sys.argv[1:] or ["log", "live"]
    cat_hist, cat_live = load_catalogs()
    shoppers = None
    if "log" in what:
        shoppers = build_log(cat_hist)
    if "live" in what:
        cache = DATA / "cache" / "history.pkl"
        if shoppers is None and cache.exists():      # skip the 5-minute replay of the history
            with open(cache, "rb") as f:
                shoppers = pickle.load(f)["shoppers"]
        elif shoppers is None:
            raise SystemExit("run `python -m offline.build_cache` (or `build_dataset log`) first")
        build_live(cat_live, shoppers)

if __name__ == "__main__":
    main()
