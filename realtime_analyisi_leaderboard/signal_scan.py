#!/usr/bin/env python3
"""Which signals do our lists leave unused? A residual scan on the clicks, inside each list.

    python realtime_analyisi_leaderboard/signal_scan.py --since "2026-11-14 15:30:00"     # UTC

For every list we served that got a click, a conditional logit: which of the ten was clicked, as a function
of its slot and of a few properties of the product for that shopper. The slot terms absorb what the ranker
already knew when it ordered the list; a property with a clearly positive coefficient is information the
order did not use (those products deserved a better slot), a negative one is a signal the ranker leans on
too much. Staying inside a list removes the mix of requests (dear or trending products are shown more in
requests that convert anyway). It is run on all ten slots and again on slots 3-10 only, where the answer
cannot come from the first two slots being far better than the average first two slots.

The property under test is collaborative: the co-purchase similarity of a product with what the shopper
bought in the 60-day history (`co_hist`) and with the products of the request's recent views (`co_view`),
from the item-item cosine of the purchase history. The ranker has no such feature (reco/features.py); the
others are in it and serve as the yardstick.

Read-only: one query on the team's feedback joined with the requests and our submissions; the purchase
history comes from the local cache in $SKORE_DATA_DIR/eda. A few seconds of one core. Needs pandas and scipy.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import sparse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(HERE))
from ab_mechanism import NEW_PRODUCTS, PRIOR, attribute_vocabulary  # noqa: E402
from rt import load_env, query  # noqa: E402

SERVED = """
SELECT f.rid AS rid, r.u AS u, r.is_new AS is_new, r.page AS page, r.rv AS rv, s.mv AS mv, f.shown AS shown,
       f.clicked AS clicked, f.purchased AS purchased
FROM (SELECT request_id::String AS rid, shown::Array(String) AS shown, clicked::String AS clicked, purchased::String AS purchased
      FROM {team}.feedback WHERE served_by = 'team' AND ts > '{since}' AND clicked::String != '') AS f
INNER JOIN (SELECT request_id::String AS rid, user_id::String AS u, is_new_user::Bool AS is_new, context.page::String AS page,
                   arrayMap(v -> v.product_id::String, recent_views::Array(JSON)) AS rv
            FROM shop.requests WHERE ts > '{since}'::DateTime64(3) - INTERVAL 1 MINUTE) AS r ON r.rid = f.rid
INNER JOIN (SELECT request_id::String AS rid, any(model_version::String) AS mv FROM {team}.submissions GROUP BY rid) AS s
        ON s.rid = f.rid"""
NAMES = ["in_sub", "attr_affinity", "co_hist", "co_view", "same_sub_last", "in_recent", "rank_in_sub", "price", "new_product"]
WHAT = {"in_sub": "a subcategory the shopper has bought in (0/1)", "attr_affinity": "log affinity for the product's attributes",
        "co_hist": "co-purchase similarity with the shopper's purchase history (1 sd inside the list)",
        "co_view": "co-purchase similarity with the recent views (1 sd inside the list)",
        "same_sub_last": "same subcategory as the last view (0/1)", "in_recent": "one of the recent views (0/1)",
        "rank_in_sub": "popularity rank inside its subcategory, log (1 sd inside the list; higher = less popular)",
        "price": "log price (1 sd inside the list)", "new_product": "added during the event (0/1)"}


def z(x: np.ndarray) -> np.ndarray:
    sd = x.std()
    return (x - x.mean()) / sd if sd > 1e-12 else np.zeros_like(x)


def fit(X: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Conditional logit by Newton's method. X: lists x items x features, y: index of the clicked item."""
    n, m, k = X.shape
    beta = np.zeros(k)
    onehot = np.zeros((n, m))
    onehot[np.arange(n), y] = 1
    for _ in range(40):
        u = X @ beta
        p = np.exp(u - u.max(1, keepdims=True))
        p /= p.sum(1, keepdims=True)
        grad = np.einsum("nm,nmk->k", onehot - p, X)
        mean = np.einsum("nm,nmk->nk", p, X)
        hess = np.einsum("nm,nmk,nml->kl", p, X, X) - mean.T @ mean + 1e-6 * np.eye(k)
        step = np.linalg.solve(hess, grad)
        beta += step
        if np.abs(step).max() < 1e-8:
            break
    return beta, np.sqrt(np.diag(np.linalg.inv(hess)))


def report(title: str, X: np.ndarray, y: np.ndarray, first_slot: int, keep: list[int]) -> None:
    n, m, _ = X.shape
    slots = np.zeros((n, m, m - 1))
    for j in range(1, m):
        slots[:, j, j - 1] = 1
    beta, se = fit(np.concatenate([slots, X[:, :, keep]], axis=2), y)
    print(f"\n{title}: {n:,} clicked lists, slots {first_slot}-{first_slot + m - 1}")
    print(f"   {'property':<14} {'coef':>7} {'se':>6} {'z':>6} {'clicks x':>9}   meaning of one unit")
    for i, j in enumerate(keep):
        b, s = beta[m - 1 + i], se[m - 1 + i]
        print(f"   {NAMES[j]:<14} {b:+7.3f} {s:6.3f} {b / s:+6.1f} {np.exp(b):9.2f}   {WHAT[NAMES[j]]}")


def main() -> None:
    try:
        from reco.priority import background
        background()
    except Exception:
        pass
    since = sys.argv[sys.argv.index("--since") + 1]
    load_env()
    req = pd.DataFrame(query(SERVED.format(team=os.environ["TEAM_ID"], since=since))["data"])
    req["is_new"] = req.is_new.astype(bool)
    cache = Path(os.environ.get("SKORE_DATA_DIR", ROOT / "data")) / "eda"
    cat = pd.read_parquet(cache / "catalog.parquet", columns=["product_id", "subcategory", "price_eur", "description"])
    known_products = set(cat.product_id)
    new = pd.DataFrame(query(NEW_PRODUCTS)["data"])
    cat = pd.concat([cat, new], ignore_index=True).drop_duplicates("product_id").reset_index(drop=True)
    index = {p: i for i, p in enumerate(cat.product_id)}
    sub = cat.subcategory.to_numpy()
    price = np.log(cat.price_eur.fillna(cat.price_eur.median()).to_numpy())
    is_new_product = np.array([p not in known_products for p in cat.product_id], dtype=float)
    voc = attribute_vocabulary(cat.description)
    a_index = {a: i for i, a in enumerate(sorted(voc))}

    def attrs_of(text: str) -> list[int]:
        text, out = str(text).lower(), []
        for a in voc:
            if a in text:
                out.append(a_index[a])
                text = text.replace(a, " ")
        return out

    attrs = [attrs_of(t) for t in cat.description]
    hist = pd.read_parquet(cache / "purchases.parquet", columns=["user_id", "product_id"]).drop_duplicates()
    hist["p"] = hist.product_id.map(index)
    hist = hist.dropna(subset=["p"])
    hist["p"] = hist.p.astype(int)
    counts = np.bincount(hist.p, minlength=len(index)).astype(float)
    rank = pd.Series(-counts).groupby(sub).rank(method="first").to_numpy()        # 1 = best seller of its subcategory
    g = np.zeros(len(a_index))
    for i, c in enumerate(counts):
        for a in attrs[i]:
            g[a] += c
    g /= counts.sum()
    users = hist.user_id.astype("category")
    B = sparse.csr_matrix((np.ones(len(hist), np.float32), (users.cat.codes.to_numpy(), hist.p.to_numpy())),
                          shape=(len(users.cat.categories), len(index)))
    C = (B.T @ B).toarray()
    d = np.sqrt(np.diag(C))
    d[d == 0] = 1
    S = C / d[:, None] / d[None, :]                                               # item-item cosine of the purchase history
    np.fill_diagonal(S, 0)
    bought = hist[hist.user_id.isin(req.u.unique())].groupby("user_id").p.apply(np.array).to_dict()

    rows, clicked, meta = [], [], []
    top = {"co_hist": [0, 0.0, 0], "co_view": [0, 0.0, 0]}
    for r in req.itertuples(index=False):
        shown = [index.get(p) for p in r.shown]
        if len(shown) != 10 or None in shown or r.clicked not in r.shown:
            continue
        shown = np.array(shown)
        H = bought.get(r.u)
        rv = [index[p] for p in r.rv if p in index]
        x = np.zeros((10, len(NAMES)))
        if H is not None and len(H):
            subs = set(sub[H])
            profile = np.zeros(len(a_index))
            for h in H:
                for a in attrs[h]:
                    profile[a] += 1
            x[:, 0] = [sub[i] in subs for i in shown]
            x[:, 1] = [np.log(np.mean([((profile[a] + PRIOR * g[a]) / (len(H) + PRIOR)) / g[a] for a in attrs[i]])) if attrs[i] else 0.0 for i in shown]
            x[:, 2] = z(np.log1p(50 * S[H][:, shown].sum(0)))
        if rv:
            x[:, 3] = z(np.log1p(50 * S[rv][:, shown].sum(0)))
            x[:, 4] = sub[shown] == sub[rv[-1]]
            x[:, 5] = np.isin(shown, rv)
        x[:, 6] = z(np.log(rank[shown]))
        x[:, 7] = z(price[shown])
        x[:, 8] = is_new_product[shown]
        rows.append(x)
        clicked.append(r.shown.index(r.clicked))
        meta.append((r.is_new, H is not None and len(H) > 0, bool(rv)))
    X, y, meta = np.array(rows), np.array(clicked), np.array(meta)
    weight = np.bincount(y, minlength=10) / len(y)
    print(f"clicked lists since {since} UTC: {len(y):,}; clicks by slot: " + " ".join(f"{100 * w:.0f}%" for w in weight))
    for name, col in (("co_hist", 2), ("co_view", 3)):                             # the plain version of the same question
        ok = X[:, :, col].std(1) > 0
        best = X[ok, :, col].argmax(1)
        print(f"   lists where {name} differs between products: {int(ok.sum()):,}; its best product got the click in "
              f"{100 * (best == y[ok]).mean():.1f}% of them, its slot alone predicts {100 * weight[best].mean():.1f}%")

    known = ~meta[:, 0] & meta[:, 1]
    report("KNOWN shoppers with a purchase history", X[known], y[known], 1, list(range(9)))
    report("the same without the co-purchase terms (yardstick: what the used signals look like)", X[known], y[known], 1, [0, 1, 4, 5, 6, 7, 8])
    deep = known & (y >= 2)
    report("KNOWN shoppers, clicks in slots 3-10 only", X[deep][:, 2:, :], y[deep] - 2, 3, list(range(9)))
    fresh = meta[:, 0] & meta[:, 2]
    report("NEW shoppers with recent views", X[fresh], y[fresh], 1, [3, 4, 5, 6, 7, 8])
    deep = fresh & (y >= 2)
    report("NEW shoppers, clicks in slots 3-10 only", X[deep][:, 2:, :], y[deep] - 2, 3, [3, 4, 5, 6, 7, 8])


if __name__ == "__main__":
    main()
