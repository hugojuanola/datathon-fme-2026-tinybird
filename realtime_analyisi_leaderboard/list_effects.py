#!/usr/bin/env python3
"""Do the products of a list take clicks from each other? Tested with the ranker's own prediction held equal.

    python realtime_analyisi_leaderboard/list_effects.py

The ranker scores each product on its own and sorts. That is the best order only if what one product gets
does not depend on its neighbours. The feedback records at most one click per request, and a shopper who
wants a subcategory finds it in the first product of that subcategory: the second and third may be worth
less than their score says, and a product of another subcategory more. If so, a list should be spread.

The data: the model session's table of lists v9 was not trained on (14 Nov, 17:00-20:20 UTC, 30,893 lists),
with v9's predicted click and purchase probability for every product shown at the slot it was shown
($SKORE_DATA_DIR/cf_carousel.parquet, built by their cf_carousel.py). For each product: is it the first of
its subcategory (category, brand) in the list, the second, the third or later.

Three reads, from the plainest to the strictest:
1. observed against predicted clicks and purchases by that position, overall and by slot band;
2. a conditional logit inside each clicked (bought) list on the slot, log of v9's prediction and the
   position within the subcategory: the control that slot dummies alone cannot give;
3. the ten products reordered greedily with a penalty on repeats: where does the product that was clicked
   (bought) end up? This last test leans towards the order that was served, because clicks follow the slot.

Read-only and light: local files only, no model is run. Needs pandas.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
from signal_scan import fit  # noqa: E402


def ratio_table(df: pd.DataFrame, key: str, title: str) -> None:
    g = df.groupby(key, observed=True).agg(impressions=("click", "size"), clicks=("click", "sum"), pc=("pc", "sum"),
                                           buys=("buy", "sum"), pb=("pb", "sum"), slot=("slot", "mean"))
    g["clicks obs/pred"] = g.clicks / (g.pc * df.click.sum() / df.pc.sum())
    g["se"] = np.sqrt(g.clicks.clip(lower=1)) / (g.pc * df.click.sum() / df.pc.sum())
    g["buys obs/pred"] = g.buys / (g.pb * df.buy.sum() / df.pb.sum())
    g["se "] = np.sqrt(g.buys.clip(lower=1)) / (g.pb * df.buy.sum() / df.pb.sum())
    print(f"\n{title}")
    print(g[["impressions", "slot", "clicks", "clicks obs/pred", "se", "buys", "buys obs/pred", "se "]].round(2).to_string())


def logit(df: pd.DataFrame, flag: str, pred: str, names: list[str], title: str) -> None:
    lists = df[df.request.isin(df.loc[df[flag], "request"])]
    lists = lists[lists.groupby("request").slot.transform("size") == 10].sort_values(["request", "slot"])
    n = lists.request.nunique()
    y = lists[flag].to_numpy().reshape(n, 10).argmax(1)
    slots = np.zeros((n, 10, 9))
    for j in range(1, 10):
        slots[:, j, j - 1] = 1
    X = np.concatenate([slots, np.log(lists[pred].clip(lower=1e-9)).to_numpy().reshape(n, 10, 1),
                        lists[names].to_numpy(dtype=float).reshape(n, 10, len(names))], axis=2)
    beta, se = fit(X, y)
    print(f"\n{title}: {n:,} lists")
    print(f"   {'term':<34} {'coef':>7} {'se':>6} {'z':>6} {'chosen x':>9}")
    for i, name in enumerate(["log of v9's prediction"] + names):
        b, s = beta[9 + i], se[9 + i]
        print(f"   {name:<34} {b:+7.3f} {s:6.3f} {b / s:+6.1f} {np.exp(b):9.2f}")


def rerank(df: pd.DataFrame, penalty: float, key: str) -> np.ndarray:
    """New rank (1..10) of every product when the ten are picked greedily by score x penalty ** (repeats already placed)."""
    out = np.zeros(len(df), dtype=int)
    score, group = df.s.to_numpy(), df[key].to_numpy()
    for start in range(0, len(df), 10):
        s, g = score[start:start + 10].copy(), group[start:start + 10]
        placed: dict = {}
        left = list(range(10))
        for rank in range(1, 11):
            best = max(left, key=lambda i: s[i] * penalty ** placed.get(g[i], 0))
            out[start + best] = rank
            placed[g[best]] = placed.get(g[best], 0) + 1
            left.remove(best)
    return out


def main() -> None:
    try:
        from reco.priority import background
        background()
    except Exception:
        pass
    from offline.build_dataset import load_catalogs
    _, cat = load_catalogs()
    data = Path(os.environ.get("SKORE_DATA_DIR", ROOT / "data"))
    df = pd.read_parquet(data / "cf_carousel.parquet", columns=["request", "item", "slot", "click", "buy", "pc", "pb", "s"])
    df = df[df.groupby("request").slot.transform("size") == 10].sort_values(["request", "slot"]).reset_index(drop=True)
    item = df.item.to_numpy()
    for key, codes in (("sub", cat.sub), ("cat", cat.cat), ("brand", cat.brand)):
        df[key] = np.asarray(codes)[item]
        df[f"nth_{key}"] = df.groupby(["request", key]).cumcount() + 1
        df[f"pos_{key}"] = pd.Categorical(np.where(df[f"nth_{key}"] == 1, "first", np.where(df[f"nth_{key}"] == 2, "second", "third or later")),
                                          categories=["first", "second", "third or later"])
        df[f"second_{key}"] = (df[f"nth_{key}"] == 2).astype(float)
        df[f"later_{key}"] = (df[f"nth_{key}"] >= 3).astype(float)
    df["band"] = pd.cut(df.slot, [0, 1, 3, 6, 10], labels=["slot 1", "slots 2-3", "slots 4-6", "slots 7-10"])
    per_list = df.groupby("request").agg(subs=("sub", "nunique"), cats=("cat", "nunique"), clicks=("click", "sum"), pc=("pc", "sum"),
                                         buys=("buy", "sum"), pb=("pb", "sum"))
    print(f"lists: {len(per_list):,}; clicks {int(df.click.sum()):,}; purchases {int(df.buy.sum()):,}; a list holds {per_list.subs.mean():.1f} "
          f"subcategories and {per_list.cats.mean():.1f} categories on average; share of impressions that repeat a subcategory already "
          f"shown above: {100 * (df.nth_sub > 1).mean():.1f}%")

    ratio_table(df, "band", "0) is v9 calibrated by slot? (observed over predicted, the overall level taken out)")
    ratio_table(df, "pos_sub", "1) by position within its SUBCATEGORY in the list")
    ratio_table(df[df.slot > 1], ["band", "pos_sub"], "   the same by slot band")
    ratio_table(df, "pos_cat", "   by position within its CATEGORY in the list")
    ratio_table(df, "pos_brand", "   by position within its BRAND in the list")
    per_list["spread"] = pd.cut(per_list.subs, [0, 3, 5, 7, 10], labels=["1-3 subcategories", "4-5", "6-7", "8-10"])
    g = per_list.groupby("spread", observed=True).agg(lists=("clicks", "size"), clicks=("clicks", "sum"), pc=("pc", "sum"), buys=("buys", "sum"), pb=("pb", "sum"))
    g["clicks obs/pred"] = g.clicks / (g.pc * df.click.sum() / df.pc.sum())
    g["buys obs/pred"] = g.buys / (g.pb * df.buy.sum() / df.pb.sum())
    print("\n   whole lists, by how many subcategories they hold")
    print(g.round(2).to_string())

    for flag, pred, what in (("click", "pc", "clicks"), ("buy", "pb", "purchases")):
        logit(df, flag, pred, ["second_sub", "later_sub"], f"2) conditional logit on {what}: slot + v9's prediction + position within the subcategory")
        logit(df, flag, pred, ["second_sub", "later_sub", "second_cat", "later_cat", "second_brand", "later_brand"],
              f"   the same with category and brand ({what})")

    print("\n3) the ten reordered greedily by v9's score x penalty ** (products of the same subcategory already placed):")
    weight = df.groupby("slot").buy.mean().to_numpy()
    weight = weight / weight[0]
    cw = df.groupby("slot").click.mean().to_numpy()
    cw = cw / cw[0]
    served = df.slot.to_numpy().astype(int)
    print(f"   {'order':<28} {'click: recip. rank':>18} {'slot value':>10} {'buy: recip. rank':>17} {'slot value':>10} {'lists changed':>13}")
    for label, rank in [("as served", served), ("v9's score alone", rerank(df, 1.0, "sub"))] + [
            (f"penalty {p} per repeat", rerank(df, p, "sub")) for p in (0.9, 0.8, 0.7, 0.5)] + [
            (f"category penalty {p}", rerank(df, p, "cat")) for p in (0.9, 0.8)]:
        c, b = df.click.to_numpy(), df.buy.to_numpy()
        base = rerank(df, 1.0, "sub")
        changed = (rank != base).reshape(-1, 10).any(1).mean()
        print(f"   {label:<28} {np.mean(1 / rank[c]):18.4f} {np.mean(cw[rank[c] - 1]):10.4f} {np.mean(1 / rank[b]):17.4f} "
              f"{np.mean(weight[rank[b] - 1]):10.4f} {100 * changed:12.1f}%")


if __name__ == "__main__":
    main()
