"""Offline evaluation on what shoppers do next: is what a shopper buys right after a request in our top 10?

    python -m offline.next_purchase [hours, default 6] [max requests, default 3000]

Our own feedback only tells how the 10 products we showed did, and a live A/B needs hours to tell two
rankers apart (docs/findings.md §15). The organic stream answers a sharper question for free: every request
is followed, for about 7 % of shoppers, by a purchase in the store within half an hour. A ranker that
understands the shopper should have had that product in its list. No ranker chose what was bought, so the
comparison is fair between rankers, and there are thousands of such purchases per hour.

The live stream is replayed in time order (same Shopper updates, prices and trend detector as the server);
at each sampled request the rules retrieve their 1,000 candidates, the features are built once, and every
ranker in models/ orders them. For each product the shopper bought in the next 30 minutes (and had not
bought before) we note where each ranker put it.

    hit@10     share of those purchases that were in the ranker's first 10
    weighted   the same, a hit counting as much as the attention its slot gets (slot 1 = 1, slot 10 = 0.15)
    retrieved  share that were among the 1,000 candidates at all (the ceiling for every ranker)

It is not the organisers' metric: a shopper who goes and buys something was looking for it, and a carousel
also has to tempt the one who was not. It is the fast, unbiased first filter before an arm goes live.
"""
from __future__ import annotations

import pickle
import sys
from typing import Callable, Iterator

import numpy as np
import pandas as pd

from offline.build_dataset import live_events, live_feedback, load_catalogs
from reco.features import (DEVICES, F, PAGES, REGIONS, Catalog, Shopper, Trends, featurize, group_keys, trend_vector,
                           usual_shares)
from reco.priority import background
from reco.rawtree import DATA, ROOT
from reco.recommend import CANDIDATES, Ranker, score_rules

HORIZON = 1800                                   # seconds after the request in which a purchase counts
SLOT_WEIGHT = np.array([21483, 12015, 8805, 6836, 5629, 5043, 4438, 3923, 3483, 3260]) / 21483  # clicks per slot in the log


def stream(cat: Catalog, shoppers: dict[str, Shopper], events: pd.DataFrame, requests: pd.DataFrame,
           live: bool = True) -> Iterator[tuple]:
    """Replay the store in time order and stop at every request.

    Yields (index, request, time in seconds, shopper or None, recent views as product indices, trend vector)
    with the shopper, the prices and the trend detector as they were at that moment — what the server knew.
    When the caller comes back for the next request, the carousel purchase of this one (if any) is applied.
    live: prices change and trends are detected (the history has neither).
    """
    pos = cat.pos
    events = events[events.product_id.isin(pos)]
    ev_ts, ev_type = events.ts.to_numpy(), events.ev.to_numpy()
    ev_user, ev_item = events.user_id.to_numpy(), events.product_id.map(pos).to_numpy()
    sub_of, log_price, brand_of, attrs_of = cat.sub.tolist(), cat.log_price.tolist(), cat.brand.tolist(), cat.attr_ids
    moves, k = (list(getattr(cat, "price_moves", [])) if live else []), 0
    base_log = cat.log_price - cat.discount
    trends, usual, groups_of = Trends(), usual_shares(cat), group_keys(cat)
    trend, trend_at = None, 0
    j, n_ev = 0, len(ev_ts)
    for i, r in enumerate(requests.itertuples(index=False)):
        t = int(r.ts_ms) // 1000
        while j < n_ev and ev_ts[j] <= t:                       # the store up to this request
            u = shoppers.get(ev_user[j])
            if u is None:
                u = shoppers[ev_user[j]] = Shopper()
            item, kind = int(ev_item[j]), ev_type[j]
            if kind == "v":
                u.view(sub_of[item], attrs_of[item])
                if live:
                    trends.add(int(ev_ts[j]) // 60, groups_of[item], False)
            elif kind == "a":
                u.cart(item, int(ev_ts[j]), attrs_of[item], sub_of[item])
            else:
                u.buy(item, sub_of[item], log_price[item], attrs_of[item], brand_of[item])
                if live:
                    trends.add(int(ev_ts[j]) // 60, groups_of[item], True)
            j += 1
        while k < len(moves) and moves[k][0] <= t:              # prices as they were
            _, item, price = moves[k]
            cat.log_price[item] = log_price[item] = float(np.log(max(price, 0.5)))
            cat.discount[item] = cat.log_price[item] - base_log[item]
            cat.static[item, F["log_price"]], cat.static[item, F["discount"]] = cat.log_price[item], cat.discount[item]
            k += 1
        if live and t - trend_at >= 5:                          # the detector, as the server runs it
            trend, trend_at = trend_vector(cat, trends.lifts(*usual)), t
            trends.forget()
        shopper = shoppers.get(r.user_id)
        yield i, r, t, shopper, ([pos[p] for p in r.rv.split(",") if p in pos] if r.rv else []), trend
        if r.purchased and r.purchased in pos and shopper is not None:     # sold through a carousel: satiated
            shopper.sold(pos[r.purchased], sub_of[pos[r.purchased]])


def bought_later(events: pd.DataFrame, cat: Catalog) -> Callable[[str, int], np.ndarray]:
    """later(user, t) → the product indices that shopper buys in the store in the HORIZON after t."""
    bought = events[(events.ev == "p") & events.product_id.isin(cat.pos)]
    by_user = {u: (g.ts.to_numpy(), g.product_id.map(cat.pos).to_numpy()) for u, g in bought.groupby("user_id")}
    nothing = (np.zeros(0), np.zeros(0, dtype=int))

    def later(user: str, t: int) -> np.ndarray:
        ts, items = by_user.get(user, nothing)
        return items[np.searchsorted(ts, t, side="right"):np.searchsorted(ts, t + HORIZON, side="right")]
    return later


def candidates(cat: Catalog, shopper: Shopper | None, recent: list[int]) -> tuple[np.ndarray, np.ndarray]:
    """(the rules' 1,000 candidates best first, the rules' own score of every product), as recommend() does."""
    rules, retrieval = score_rules(cat, shopper, recent), score_rules(cat, shopper, recent, retrieval=True)
    blocked = [b for b in (shopper.bought if shopper else ()) if b < len(rules)]
    rules[blocked] = retrieval[blocked] = -1.0
    top = np.argpartition(-retrieval, CANDIDATES - 1)[:CANDIDATES]
    return top[np.argsort(-retrieval[top], kind="stable")], rules


def collect(hours: float, limit: int, rankers: dict[str, Ranker], variants: dict | None = None) -> pd.DataFrame:
    """One row per (sampled request, product bought within HORIZON): the rank every ranker gave it.

    variants: {label: function(x, scores of every ranker, cat, shopper, candidates, trend) -> scores}: other
    ways of ordering the same candidates (blends, lifts), judged on the same purchases.
    """
    _, cat = load_catalogs()
    with open(DATA / "cache" / "history.pkl", "rb") as f:
        shoppers: dict[str, Shopper] = pickle.load(f)["shoppers"]
    events, requests = live_events(), live_feedback()
    later, end = bought_later(events, cat), int(events.ts.iloc[-1])
    t_req = (requests.ts_ms // 1000).to_numpy()
    window = (t_req >= end - int(3600 * hours)) & (t_req <= end - HORIZON)
    followed = np.array([w and len(later(u, t)) > 0 for w, u, t in zip(window, requests.user_id, t_req)])
    chosen = np.flatnonzero(followed)
    if len(chosen) > limit:
        chosen = np.sort(np.random.default_rng(0).choice(chosen, limit, replace=False))
    sampled = np.zeros(len(requests), bool)
    sampled[chosen] = True
    print(f"requests {clock(t_req[window].min())}-{clock(t_req[window].max())} UTC: {int(window.sum()):,}; followed by a purchase "
          f"within {HORIZON // 60} min: {int(followed.sum()):,} ({followed.sum() / window.sum():.1%}); evaluated: {len(chosen):,}", flush=True)

    rows = []
    for i, r, t, shopper, recent, trend in stream(cat, shoppers, events, requests):
        if not sampled[i]:
            continue
        known = shopper.bought if shopper else set()
        targets = [int(p) for p in dict.fromkeys(later(r.user_id, t).tolist()) if p not in known]
        if not targets:
            continue
        top, rules = candidates(cat, shopper, recent)
        x = featurize(cat, shopper, PAGES.get(r.page, 2), DEVICES.get(r.device, 0), REGIONS.get(r.region, -1),
                      recent, top, float(t), slot=1.0)
        where = {int(p): n for n, p in enumerate(top)}
        rules_rank = np.argsort(np.argsort(-rules, kind="stable"), kind="stable")
        scores = {name: ranker.score(x) for name, ranker in rankers.items()}
        for label, fn in (variants or {}).items():
            scores[label] = fn(x, scores, cat, shopper, top, trend)
        ranks = {name: np.argsort(np.argsort(-s, kind="stable"), kind="stable") for name, s in scores.items()}
        last = recent[-1] if recent else None
        for p in targets:
            row = {"request": i, "new": bool(r.is_new), "page": r.page, "n_recent": len(recent),
                   "retrieved": p in where, "rules": int(rules_rank[p]),
                   "viewed": p in recent, "carted": bool(shopper and p in shopper.carted),
                   "same_sub": last is not None and cat.sub[p] == cat.sub[last],
                   "same_cat": last is not None and cat.cat[p] == cat.cat[last],
                   "bought_sub": bool(shopper and cat.sub[p] in shopper.sub_purch),
                   "trending": trend is not None and trend[p] > 1, "new_product": bool(cat.is_new[p]),
                   "pop_rank_in_sub": int((cat.pop[cat.by_sub[cat.sub[p]]] > cat.pop[p]).sum()) + 1}
            for name, rank in ranks.items():
                row[name] = int(rank[where[p]]) if p in where else 10**6
            rows.append(row)
        if len(rows) % 500 < len(targets):
            print(f"   {len(rows):,} purchases placed", flush=True)
    return pd.DataFrame(rows)


def clock(seconds: float) -> str:
    return pd.to_datetime(seconds, unit="s").strftime("%H:%M")


def table(df: pd.DataFrame, names: list[str], label: str) -> None:
    out = {}
    for name in names:
        rank = df[name].to_numpy()
        hit = rank < 10
        out[name] = {"hit@10 %": 100 * hit.mean(), "weighted %": 100 * np.where(hit, SLOT_WEIGHT[np.clip(rank, 0, 9)], 0).mean(),
                     "first %": 100 * (rank == 0).mean(), "in top 30 %": 100 * (rank < 30).mean()}
    se = 100 * np.sqrt(0.12 * 0.88 / max(len(df), 1))
    print(f"\n{label}: {len(df):,} purchases (retrieved among the 1,000 candidates: {100 * df.retrieved.mean():.1f} %; "
          f"one standard error of a hit rate ≈ {se:.1f} points)")
    print(pd.DataFrame(out).T.round(1).to_string())


def report(df: pd.DataFrame, names: list[str]) -> None:
    table(df, names, "all shoppers")
    table(df[~df.new], names, "known shoppers")
    table(df[df.new], names, "new shoppers")
    best = max(names, key=lambda n: (df[n] < 10).mean())
    print(f"\nwhere the purchases are, and how many of them {best} had in its 10:")
    for key in ("viewed", "carted", "bought_sub", "same_sub", "same_cat", "trending", "new_product"):
        g = df.groupby(key).agg(purchases=(best, "size"), hit=(best, lambda s: 100 * (s < 10).mean()),
                                retrieved=("retrieved", lambda s: 100 * s.mean()))
        print(f"   {key:<12}" + " · ".join(f"{'yes' if k else 'no'}: {int(r.purchases):>5} purchases, hit {r.hit:4.1f} %, retrieved {r.retrieved:5.1f} %"
                                           for k, r in g.iterrows()))


def main() -> None:
    background()
    args = [a for a in sys.argv[1:] if a.replace(".", "").isdigit()]
    hours, limit = (float(args[0]) if args else 6.0), (int(args[1]) if len(args) > 1 else 3000)
    rankers = {p.name: Ranker(p) for p in sorted((ROOT / "models").iterdir()) if (p / "conv.txt").exists()}
    df = collect(hours, limit, rankers)
    df.to_parquet(DATA / "next_purchase.parquet", index=False)
    report(df, ["rules"] + list(rankers))


if __name__ == "__main__":
    main()
