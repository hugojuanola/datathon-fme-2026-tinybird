"""Train a ranker, validate it on data it has not seen, then refit it on everything for deployment.

    python -m offline.build_dataset [log|live]
    python -m offline.train NAME         # → models/NAME/{click,conv}.txt + a validation report

Two small gradient-boosted models, multiplied at serving time:

    P(purchase | shown) = P(click | shown, slot) × P(purchase | click)

Clicks are 3× more frequent than purchases, so the click model has more to learn from; the second model
only has to say which clicked products end up in the basket.

1. Validation fit. The future is held out: the last 7 days of the log and the last quarter of our live
   feedback (the real simulator — the only place where cross-category recommendations and satiation exist).
   It chooses the number of trees and produces the report: on held-out live feedback, with the slot hidden
   from the model, how high does each ranker in models/ place the product that was clicked / bought among
   the 10 shown? Each click is weighted by the inverse of the attention its slot got, so a ranker is not
   rewarded for agreeing with the order the products happened to be shown in.
2. Deployment fit. Same settings, all the data, that number of trees (+10 %): the model that goes live has
   also seen the most recent feedback.

Rows where the shopper had already bought the product are dropped: live, those are never shown.
"""
from __future__ import annotations

import sys

import lightgbm as lgb
import numpy as np
import pandas as pd

from reco.features import CATEGORICAL, FEATURES
from reco.priority import background
from reco.rawtree import DATA, ROOT

MODELS = ROOT / "models"
CUT_LOG = pd.Timestamp("2026-11-07").value // 10**6     # ms: the log is split here
LIVE_VALID = 0.25                                       # last share of the live feedback held out
LIVE_WEIGHT = 5.0                                       # a live row counts as this many log rows
PARAMS = dict(objective="binary", learning_rate=0.05, num_leaves=31, max_depth=6, min_data_in_leaf=300,
              feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1, lambda_l2=10.0,
              verbose=-1, num_threads=6, seed=0)
SLOT_ATTENTION = np.array([21483, 12015, 8805, 6836, 5629, 5043, 4438, 3923, 3483, 3260]) / 21483   # clicks per slot in the log


def load(live_weight: float = LIVE_WEIGHT) -> tuple[pd.DataFrame, pd.Series]:
    """(training table, mask of the held-out rows)."""
    df = pd.concat([pd.read_parquet(DATA / "train_log.parquet"), pd.read_parquet(DATA / "train_live.parquet")],
                   ignore_index=True)
    df = df[~df.bought_before].reset_index(drop=True)
    for name in FEATURES:       # a feature newer than a table: absent there means "nothing special" (no trend)
        if name not in df:
            df[name] = 0.0
    df["trend"] = df["trend"].fillna(0.0)
    live = df.source == "live"
    live_cut = df.ts_ms[live].quantile(1 - LIVE_VALID)
    valid = np.where(live, df.ts_ms >= live_cut, df.ts_ms >= CUT_LOG)
    df.loc[live, "weight"] *= live_weight
    return df, pd.Series(valid, index=df.index)


def fit(df: pd.DataFrame, valid: pd.Series, target: str, features: list[str], rounds: int = 2000) -> lgb.Booster:
    """Fit on the rows before the cut, stop when the held-out rows stop improving."""
    cats = [c for c in CATEGORICAL if c in features]
    train = lgb.Dataset(df.loc[~valid, features], df.loc[~valid, target], weight=df.loc[~valid, "weight"],
                        categorical_feature=cats, free_raw_data=False)
    held = lgb.Dataset(df.loc[valid, features], df.loc[valid, target], weight=df.loc[valid, "weight"], reference=train)
    return lgb.train(PARAMS, train, rounds, valid_sets=[held],
                     callbacks=[lgb.early_stopping(100, verbose=False)])


def refit(df: pd.DataFrame, target: str, features: list[str], trees: int) -> lgb.Booster:
    cats = [c for c in CATEGORICAL if c in features]
    return lgb.train(PARAMS, lgb.Dataset(df[features], df[target], weight=df["weight"], categorical_feature=cats), trees)


def score(click: lgb.Booster, conv: lgb.Booster, rows: pd.DataFrame) -> np.ndarray:
    """What the ranker would score these rows with, not knowing where they were shown."""
    x = rows.assign(slot=1.0, is_live=1.0)      # is_live: a constant some older rankers expect
    return click.predict(x[click.feature_name()]) * conv.predict(x[conv.feature_name()])


def ranking_quality(rows: pd.DataFrame, s: np.ndarray) -> dict:
    """Among the 10 products shown, where does the ranker put the one that was clicked / bought?"""
    weight = 1 / SLOT_ATTENTION[rows.slot.astype(int).to_numpy() - 1]
    rank = rows.assign(s=s).groupby("request").s.rank(ascending=False, method="first").to_numpy()
    out = {}
    for target in ("click", "buy"):
        hit = rows[target].to_numpy()
        out[f"{target}: reciprocal rank"] = np.average(1 / rank[hit], weights=weight[hit])
        out[f"{target}: ranked first"] = np.average(rank[hit] <= 1, weights=weight[hit])
        out[f"{target}: in top 3"] = np.average(rank[hit] <= 3, weights=weight[hit])
    return out


def main() -> None:
    background()   # never compete with the live loop for the CPU
    name = sys.argv[1] if len(sys.argv) > 1 else "candidate"
    df, valid = load()
    held = df[valid & (df.source == "live")]
    print(f"{name}: {len(FEATURES)} features, {len(df):,} rows ({(df.source == 'live').sum():,} live, weight ×{LIVE_WEIGHT:g}); "
          f"held-out live: {held.request.nunique():,} requests, {int(held.click.sum())} clicks, {int(held.buy.sum())} purchases")

    clicked = df.click
    conv_features = [f for f in FEATURES if f != "slot"]      # position decides what is looked at, not what is bought
    click = fit(df, valid, "click", FEATURES)
    conv = fit(df[clicked], valid[clicked], "buy", conv_features, rounds=600)

    rankers = {p.name: (lgb.Booster(model_file=str(p / "click.txt")), lgb.Booster(model_file=str(p / "conv.txt")))
               for p in sorted(MODELS.iterdir()) if p.name != name and (p / "conv.txt").exists()}
    rankers[f"{name} (validation fit)"] = (click, conv)
    for label, rows in (("all requests", held), ("known shoppers", held[held.is_new == False]),      # noqa: E712
                        ("new shoppers", held[held.is_new == True])):                                # noqa: E712
        table = pd.DataFrame({r: ranking_quality(rows, score(*models, rows)) for r, models in rankers.items()}).T
        print(f"\nheld-out live feedback, {label}: {rows.request.nunique():,} requests, {int(rows.buy.sum())} purchases")
        print(table.round(3).to_string())

    click_all = refit(df, "click", FEATURES, int(click.best_iteration * 1.1))
    conv_all = refit(df[clicked], "buy", conv_features, int(conv.best_iteration * 1.1))
    (MODELS / name).mkdir(parents=True, exist_ok=True)
    click_all.save_model(MODELS / name / "click.txt")
    conv_all.save_model(MODELS / name / "conv.txt")
    gain = pd.Series(click_all.feature_importance("gain"), index=FEATURES)
    print(f"\nsaved models/{name}: refit on all {len(df):,} rows, {click_all.num_trees()} + {conv_all.num_trees()} trees")
    print("click model, share of total gain:")
    print((gain / gain.sum()).sort_values(ascending=False).head(15).round(3).to_string())


if __name__ == "__main__":
    main()
