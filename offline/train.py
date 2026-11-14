"""Train the ranker and validate it on data it has not seen, in time order.

    python -m offline.build_dataset
    python -m offline.train [live_weight]   # → models/click.txt, models/conv.txt + a validation report

Two small gradient-boosted models, multiplied at serving time:

    P(purchase | shown) = P(click | shown, slot) × P(purchase | click)

Clicks are 3× more frequent than purchases, so the click model has more to learn from; the second model
only has to say which clicked products end up in the basket.

Validation is always on the future: the last 7 days of the log, and the last quarter of our live feedback
(the real simulator — the only place where cross-category recommendations and satiation exist).
Rows where the shopper had already bought the product are dropped: live, those are never shown.
"""
from __future__ import annotations

import sys

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import log_loss, roc_auc_score

from reco.features import CATEGORICAL, FEATURES
from reco.rawtree import DATA, ROOT
from reco.priority import background

MODELS = ROOT / "models"
CUT_LOG = pd.Timestamp("2026-11-07").value // 10**6     # ms: the log is split here
LIVE_VALID = 0.25                                       # last share of the live feedback held out
PARAMS = dict(objective="binary", learning_rate=0.05, num_leaves=31, max_depth=6, min_data_in_leaf=300,
              feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1, lambda_l2=10.0,
              verbose=-1, num_threads=6, seed=0)


def load(live_weight: float) -> tuple[pd.DataFrame, pd.Series]:
    df = pd.read_parquet(DATA / "train.parquet")
    df = df[~df.bought_before].reset_index(drop=True)
    live = df.source == "live"
    live_cut = df.ts_ms[live].quantile(1 - LIVE_VALID)
    valid = np.where(live, df.ts_ms >= live_cut, df.ts_ms >= CUT_LOG)
    df.loc[live, "weight"] *= live_weight
    return df, pd.Series(valid, index=df.index)


def fit(df: pd.DataFrame, valid: pd.Series, target: str, features: list[str], rounds: int = 2000) -> lgb.Booster:
    cats = [c for c in CATEGORICAL if c in features]
    train = lgb.Dataset(df.loc[~valid, features], df.loc[~valid, target], weight=df.loc[~valid, "weight"],
                        categorical_feature=cats, free_raw_data=False)
    held = lgb.Dataset(df.loc[valid, features], df.loc[valid, target], weight=df.loc[valid, "weight"], reference=train)
    return lgb.train(PARAMS, train, rounds, valid_sets=[held],
                     callbacks=[lgb.early_stopping(100, verbose=False)])


def report(name: str, y: np.ndarray, p: np.ndarray, groups: np.ndarray, is_probability: bool = True) -> dict:
    """AUC / log-loss per impression, and how high the model would rank the product that got the click/purchase
    among the 10 shown (mean reciprocal rank; 1.0 = always first, 0.29 = random order)."""
    order = np.lexsort((-p, groups))
    rank = np.empty(len(p), dtype=int)
    _, start = np.unique(groups[order], return_index=True)
    rank[order] = np.arange(len(p)) - np.repeat(start, np.diff(np.append(start, len(p)))) + 1
    return {"set": name, "positives": int(y.sum()), "auc": roc_auc_score(y, p),
            "logloss": log_loss(y, p, labels=[0, 1]) if is_probability else np.nan,
            "mrr": (1 / rank[y.astype(bool)]).mean()}


def main() -> None:
    background()   # never compete with the live loop for the CPU
    live_weight = float(sys.argv[1]) if len(sys.argv) > 1 else 5.0
    df, valid = load(live_weight)
    print(f"{len(df):,} rows ({(df.source == 'live').sum():,} live), live weight ×{live_weight:g}\n")

    click = fit(df, valid, "click", FEATURES)
    clicked = df.click
    conv_features = [f for f in FEATURES if f != "slot"]      # position decides what is looked at, not what is bought
    conv = fit(df[clicked], valid[clicked], "buy", conv_features, rounds=600)
    buy = fit(df, valid, "buy", FEATURES)

    MODELS.mkdir(exist_ok=True)
    click.save_model(MODELS / "click.txt", num_iteration=click.best_iteration)
    conv.save_model(MODELS / "conv.txt", num_iteration=conv.best_iteration)

    p_click = click.predict(df[FEATURES])
    p_conv = conv.predict(df[conv_features])
    p_buy = buy.predict(df[FEATURES])
    rows = []
    for source in ("log", "live"):
        m = (valid & (df.source == source)).to_numpy()
        g = df.request.to_numpy()[m]
        rows.append(report(f"{source}: click model → clicks", df.click.to_numpy()[m], p_click[m], g))
        rows.append(report(f"{source}: click×conv → purchases", df.buy.to_numpy()[m], (p_click * p_conv)[m], g))
        rows.append(report(f"{source}: direct purchase model", df.buy.to_numpy()[m], p_buy[m], g))
        rows.append(report(f"{source}: (reference: order as shown)", df.buy.to_numpy()[m], -df.slot.to_numpy()[m], g, False))
    print(pd.DataFrame(rows).set_index("set").round(4).to_string())

    gain = pd.Series(click.feature_importance("gain"), index=FEATURES)
    print("\nclick model, share of total gain:")
    print((gain / gain.sum()).sort_values(ascending=False).head(15).round(3).to_string())
    print(f"\ntrees: click {click.best_iteration}, conv {conv.best_iteration}, buy {buy.best_iteration}")



if __name__ == "__main__":
    main()
