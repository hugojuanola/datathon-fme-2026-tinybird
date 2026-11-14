"""A second teacher for the ranker: what each shopper goes on to buy in the store, not only what a carousel sold.

    python -m offline.organic build            # → train_organic.parquet (history + live stream)
    python -m offline.organic train NAME       # → models/NAME/organic.txt, validated on the last hours
    python -m offline.organic eval NAME [hours]   # blends with the rankers in models/, on offline.next_purchase

The carousel models (offline/train.py) learn from what a carousel showed: 10 products per request, chosen by
whoever ran the carousel. The organic stream holds a much wider lesson: the product a shopper was really
after, whether or not anybody showed it. Three kinds of moment are used, each followed within half an hour
by a purchase of the same shopper somewhere in the store:

    live      a request of the live stream (about 10 % of them)
    log       a request of the old carousel (19,000 of its 2 million)
    sessions  a moment inside a purchase session of the 60-day history, written as the request it would have
              been: the shopper has just viewed a product (the last views of the session are its recent
              views) or has just arrived (none). 548,000 purchases to learn from; a sample is used.

Training rows: for each such moment, the product(s) bought (label 1) and 30 products the rules retrieved
for it and the shopper did not buy (label 0; 12 from the top 100 of the retrieval, 18 from the rest), with
the features as known at that moment — same replay, same featurize() as everything else.

The model's output is a propensity "this shopper is about to buy this product". It does not know about
slots or about being tempted by something unexpected — the carousel models do — so it is used as a factor
on top of them: score = P(click) × P(purchase | click) × organic ** power (reco.recommend).
"""
from __future__ import annotations

import pickle
import sys
import time

import lightgbm as lgb
import numpy as np
import pandas as pd

from offline.build_dataset import live_events, live_feedback, load_catalogs
from offline.next_purchase import bought_later, candidates, collect, report, stream
from reco.features import CATEGORICAL, DEVICES, FEATURES, PAGES, REGIONS, featurize
from reco.priority import background
from reco.rawtree import DATA, ROOT
from reco.recommend import Ranker

HARD, EASY = 12, 18            # negatives per request: from the top 100 of the retrieval, from the other 900
SESSION_SAMPLE = 0.22          # share of the history's purchases that give a "sessions" moment
LIVE_WEIGHT = 3.0              # a request of the live stream counts as this many of the old carousel's
VALID_HOURS = 3.0              # the last hours of the live stream are held out
BASES = ("v16", "v9")           # `eval`: the carousel rankers compared; the ones after the first are also blended with the organic model
CUT_LOG = pd.Timestamp("2026-11-07").value // 10**9     # s: history requests after this are held out too
COLUMNS = [f for f in FEATURES if f != "slot"]
PARAMS = dict(objective="binary", learning_rate=0.05, num_leaves=31, max_depth=6, min_data_in_leaf=200,
              feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1, lambda_l2=10.0,
              verbose=-1, num_threads=6, seed=0)


def rows_of(cat, shoppers, events, requests, live: bool, rng: np.random.Generator, out: list) -> None:
    """Replay one stream and emit the feature rows of every request followed by an organic purchase."""
    later = bought_later(events, cat)
    t_req = (requests.ts_ms // 1000).to_numpy()
    followed = np.array([len(later(u, t)) > 0 for u, t in zip(requests.user_id, t_req)])
    for i, r, t, shopper, recent, trend in stream(cat, shoppers, events, requests, live=live):
        if not followed[i]:
            continue
        known = shopper.bought if shopper else set()
        targets = [int(p) for p in dict.fromkeys(later(r.user_id, t).tolist()) if p not in known]
        if not targets:
            continue
        top, _ = candidates(cat, shopper, recent)
        negatives = np.concatenate([rng.choice(top[:100], HARD, replace=False), rng.choice(top[100:], EASY, replace=False)])
        idx = np.concatenate([targets, negatives[~np.isin(negatives, targets)]]).astype(int)
        # a moment taken from an organic session has no device or region: left empty, not guessed
        x = featurize(cat, shopper, PAGES.get(r.page, 2), DEVICES.get(r.device, 0) if r.device else np.nan,
                      REGIONS.get(r.region, -1) if r.region else np.nan, recent, idx, float(t), 1.0, trend)
        out.append((x, len(targets), i, t, bool(getattr(r, "is_new", False)), getattr(r, "source", "live")))


def assemble(out: list) -> pd.DataFrame:
    df = pd.DataFrame(np.concatenate([o[0] for o in out]), columns=FEATURES)
    n = [len(o[0]) for o in out]
    df["label"] = np.concatenate([np.arange(len(o[0])) < o[1] for o in out])
    df["request"] = np.repeat([o[2] for o in out], n)
    df["ts"] = np.repeat([o[3] for o in out], n)
    df["is_new"] = np.repeat([o[4] for o in out], n)
    df["source"] = np.repeat([o[5] for o in out], n)
    return df


def session_moments(events: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Moments inside the history's purchase sessions, shaped like requests (ts_ms, user_id, page, rv…).

    For a sample of the purchases: a point of the same session before it, chosen evenly between "just
    arrived" and "just viewed the k-th product". Its recent views are the last 6 products viewed until then.
    """
    views = events[events.ev == "v"]
    buys = events[events.ev == "p"]
    buys = buys[rng.random(len(buys)) < SESSION_SAMPLE]
    views = views[views.session_id.isin(buys.session_id.unique())]
    by_session = {s: (g.ts.to_numpy(), g.product_id.to_numpy()) for s, g in views.groupby("session_id", sort=False)}
    rows = []
    for user, session, t_buy in zip(buys.user_id.to_numpy(), buys.session_id.to_numpy(), buys.ts.to_numpy()):
        ts, pids = by_session.get(session, (np.zeros(0), np.zeros(0, dtype=object)))
        seen = int(np.searchsorted(ts, t_buy, side="left"))          # views of the session before the purchase
        k = int(rng.integers(0, seen + 1))
        if k == 0:
            rows.append(((int(ts[0]) if len(ts) else int(t_buy)) - 1, user, "home", ""))
        else:
            rows.append((int(ts[k - 1]), user, "product", ",".join(dict.fromkeys(pids[max(0, k - 6):k].tolist()))))
    out = pd.DataFrame(rows, columns=["t", "user_id", "page", "rv"]).drop_duplicates(["t", "user_id"])
    out["ts_ms"] = out.t * 1000
    return out.assign(device="", region="", purchased="", source="sessions").drop(columns="t")


def build() -> None:
    t0 = time.time()
    rng = np.random.default_rng(0)
    cat_hist, cat_live = load_catalogs()
    sessions = pd.read_parquet(DATA / "sessions.parquet", columns=["ts_ms", "user_id", "device", "region", "page", "rv", "purchased"])
    events = pd.read_parquet(DATA / "events.parquet", columns=["ts", "ev", "user_id", "session_id", "product_id"])
    moments = pd.concat([sessions.assign(source="log"), session_moments(events, rng)], ignore_index=True)
    moments = moments.sort_values("ts_ms", kind="stable").reset_index(drop=True)
    shoppers: dict = {}
    out: list = []
    rows_of(cat_hist, shoppers, events, moments, False, rng, out)
    log = assemble(out)
    print(f"history: {log.request.nunique():,} moments followed by a purchase ({log.groupby('source').request.nunique().to_dict()}), "
          f"{int(log.label.sum()):,} purchases, {len(log):,} rows in {time.time() - t0:.0f}s", flush=True)
    del events, sessions, moments
    cache = DATA / "cache" / "history.pkl"
    with open(cache, "rb") as f:      # the shoppers exactly as the server and the carousel table start the day with
        shoppers = pickle.load(f)["shoppers"]
    out = []
    rows_of(cat_live, shoppers, live_events(), live_feedback(), True, rng, out)
    live = assemble(out)
    print(f"live: {live.request.nunique():,} requests followed by a purchase, {int(live.label.sum()):,} purchases, "
          f"{len(live):,} rows", flush=True)
    pd.concat([log, live], ignore_index=True).to_parquet(DATA / "train_organic.parquet", index=False)
    print(f"train_organic.parquet written in {time.time() - t0:.0f}s", flush=True)


def load() -> tuple[pd.DataFrame, pd.Series]:
    df = pd.read_parquet(DATA / "train_organic.parquet")
    live = df.source == "live"
    valid = np.where(live, df.ts >= df.ts[live].max() - 3600 * VALID_HOURS, df.ts >= CUT_LOG)
    df["weight"] = np.where(live, LIVE_WEIGHT, 1.0)
    return df, pd.Series(valid, index=df.index)


def fit(df: pd.DataFrame, rounds: int, held: pd.DataFrame | None = None) -> lgb.Booster:
    cats = [c for c in CATEGORICAL if c in COLUMNS]
    train = lgb.Dataset(df[COLUMNS], df.label, weight=df.weight, categorical_feature=cats, free_raw_data=False)
    if held is None:
        return lgb.train(PARAMS, train, rounds)
    return lgb.train(PARAMS, train, rounds, valid_sets=[lgb.Dataset(held[COLUMNS], held.label, weight=held.weight, reference=train)],
                     callbacks=[lgb.early_stopping(100, verbose=False)])


def train(name: str) -> None:
    df, valid = load()
    model = fit(df[~valid], 3000, df[valid])
    held = df[valid & (df.source == "live")]
    score = pd.Series(model.predict(held[COLUMNS]), index=held.index)
    rank = score.groupby(held.request).rank(ascending=False, method="first")
    first = rank[held.label]
    print(f"{name}: {len(df):,} rows ({int(df.label.sum()):,} purchases; live {int((df.source == 'live').sum()):,} rows); "
          f"{model.best_iteration} trees")
    print(f"held-out live requests ({held.request.nunique():,}, {int(held.label.sum())} purchases): the bought product is ranked "
          f"first among its 31 in {100 * (first <= 1).mean():.1f} %, in the first 3 in {100 * (first <= 3).mean():.1f} % "
          f"(chance 3.2 % / 9.7 %)")
    folder = ROOT / "models" / name
    folder.mkdir(parents=True, exist_ok=True)
    model.save_model(folder / "organic_valid.txt")          # the fit that has not seen the last hours: for `eval`
    fit(df, max(int(model.best_iteration * 1.1), 50)).save_model(folder / "organic.txt")
    gain = pd.Series(model.feature_importance("gain"), index=COLUMNS)
    print("share of total gain:")
    print((gain / gain.sum()).sort_values(ascending=False).head(14).round(3).to_string())


def evaluate(name: str, hours: float) -> None:
    """Blends of the carousel rankers with the organic model, on the purchases that followed the last requests."""
    organic = lgb.Booster(model_file=str(ROOT / "models" / name / "organic_valid.txt"))
    columns = [FEATURES.index(c) for c in organic.feature_name()]
    rankers = {n: Ranker(ROOT / "models" / n) for n in BASES if (ROOT / "models" / n / "conv.txt").exists()}
    cache: dict = {}

    def propensity(x: np.ndarray) -> np.ndarray:
        if cache.get("x") is not x:
            cache["x"], cache["p"] = x, organic.predict(x[:, columns], num_threads=2)
        return cache["p"]

    variants = {"organic alone": lambda x, s, *_: propensity(x)}
    for base in list(rankers)[1:]:
        for power in (0.5, 1.0):
            variants[f"{base} x organic^{power:g}"] = (lambda x, s, *_, base=base, power=power: s[base] * propensity(x) ** power)
    df = collect(hours, 2500, rankers, variants)
    df.to_parquet(DATA / "next_purchase_organic.parquet", index=False)
    report(df, ["rules"] + list(rankers) + list(variants))


if __name__ == "__main__":
    background()
    what = sys.argv[1] if len(sys.argv) > 1 else "build"
    if what == "build":
        build()
    elif what == "train":
        train(sys.argv[2])
    else:
        evaluate(sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else VALID_HOURS - 0.5)
