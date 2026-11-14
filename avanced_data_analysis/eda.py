#!/usr/bin/env python3
"""Exploratory data analysis: what drives purchases in the carousel (and therefore our score).

Reads $SKORE_DATA_DIR/eda/*.parquet (run eda_pull.py first), writes the figures to figures/*.png and the headline
numbers to numbers.json, both next to this script. The findings are written up in README.md.

    python avanced_data_analysis/eda.py
"""
from __future__ import annotations

import json
import os
import sys
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import lightgbm as lgb
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest
from sklearn.metrics import roc_auc_score, silhouette_score
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "scripts"))
from rt import load_env  # noqa: E402

load_env()
D, FIG = Path(os.environ.get("SKORE_DATA_DIR", ROOT / "data")) / "eda", HERE / "figures"
FIG.mkdir(parents=True, exist_ok=True)
RNG = np.random.default_rng(0)
NUM: dict = {}

# --- house style: one fixed categorical palette, one sequential blue ramp, one diverging orange↔blue ramp ---
CAT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
BLUE, ORANGE, INK, INK2, MUTED, GRID = CAT[0], CAT[1], "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
SEQ = LinearSegmentedColormap.from_list("seq", ["#eef4fc", "#b7d3f6", "#6da7ec", "#256abf", "#0d366b"])
DIV = LinearSegmentedColormap.from_list("div", ["#c2410c", "#eb6834", "#f0efec", "#2a78d6", "#0d366b"])
plt.rcParams.update({
    "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "savefig.facecolor": "#fcfcfb",
    "axes.edgecolor": "#c3c2b7", "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": MUTED,
    "text.color": INK, "axes.titlesize": 11, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "axes.labelsize": 9, "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 8,
    "legend.frameon": False, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "font.family": "DejaVu Sans", "figure.dpi": 110,
})


def load(name: str) -> pd.DataFrame:
    df = pd.read_parquet(D / f"{name}.parquet")
    for c in df.columns:  # RawTree returns 64-bit integers as strings
        if df[c].dtype == object or str(df[c].dtype).startswith(("str", "string")):
            conv = pd.to_numeric(df[c], errors="coerce")
            if len(df) and conv.notna().all():
                df[c] = conv
    return df


def save(fig, name: str, title: str) -> None:
    fig.suptitle(title, x=0.01, ha="left", fontsize=13, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(FIG / f"{name}.png", dpi=130)
    plt.close(fig)
    print("wrote", name)


def wilson(k, n, z=1.96):
    k, n = np.asarray(k, float), np.asarray(n, float)
    p = k / n
    den = 1 + z**2 / n
    c = (p + z**2 / (2 * n)) / den
    h = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / den
    return p, c - h, c + h


def rate_bars(ax, df, by, k="buys", n="n", title="", color=BLUE, order=None, rot=0):
    g = df.groupby(by)[[k, n]].sum()
    if order is not None:
        g = g.loc[order]
    p, lo, hi = wilson(g[k], g[n])
    x = np.arange(len(g))
    ax.bar(x, 100 * p, color=color, width=0.72)
    ax.errorbar(x, 100 * p, yerr=[100 * (p - lo), 100 * (hi - p)], fmt="none", ecolor=INK2, lw=0.9, capsize=2)
    ax.set_xticks(x, [str(i) for i in g.index], rotation=rot, ha="right" if rot else "center")
    ax.set_title(title)
    ax.grid(axis="x", visible=False)
    return 100 * p


def heat(ax, m, title, cmap=SEQ, fmt="{:.2f}", center=None):
    v = m.to_numpy(float)
    kw = {}
    if center is not None:
        r = np.nanmax(np.abs(v - center))
        kw = {"vmin": center - r, "vmax": center + r}
    im = ax.imshow(v, cmap=cmap, aspect="auto", **kw)
    ax.set_xticks(range(m.shape[1]), m.columns, rotation=40, ha="right")
    ax.set_yticks(range(m.shape[0]), m.index)
    lo, hi = im.get_clim()
    for i in range(m.shape[0]):
        for j in range(m.shape[1]):
            if np.isfinite(v[i, j]) and m.size <= 150:
                dark = abs(v[i, j] - (lo + hi) / 2) > 0.28 * (hi - lo) if center is not None else v[i, j] > lo + 0.55 * (hi - lo)
                ax.text(j, i, fmt.format(v[i, j]), ha="center", va="center", fontsize=7, color="white" if dark else INK)
    ax.set_title(title)
    ax.grid(False)
    return im


# =========================================================================================================
cat = load("catalog")
pe, pc = load("product_events"), load("product_carousel")
users, ucat = load("users"), load("user_category")
evh, catd, rc = load("events_hourly"), load("category_daily"), load("region_category")
seg, sd, pur, ss = load("sessions_segments"), load("sessions_daily"), load("purchases"), load("sessions_sample")
lr, lf = load("live_requests"), load("live_feedback")

prod = cat.merge(pe, on="product_id", how="left").merge(pc, on="product_id", how="left").fillna(
    {"impressions": 0, "clicks": 0, "buys": 0})
prod["cart_rate"] = prod.carts / prod.views
prod["buy_rate"] = prod.purchases / prod.carts.clip(lower=1)
prod["view_to_buy"] = prod.purchases / prod.views
prod["age_days"] = (pd.Timestamp("2026-11-14") - pd.to_datetime(prod.created_at.str[:19])).dt.days
prod["trend"] = np.log2((prod.purchases_last7d + 3) / (prod.purchases_first7d + 3))

# ---------------------------------------------------------------------------------------------------------
# 1. UNIVARIATE
# ---------------------------------------------------------------------------------------------------------
fig, ax = plt.subplots(2, 3, figsize=(14, 7.6))
a = ax[0, 0]
a.hist(prod.price_eur, bins=np.logspace(np.log10(1.5), np.log10(700), 45), color=BLUE, edgecolor="#fcfcfb", lw=0.4)
a.set_xscale("log")
a.axvline(prod.price_eur.median(), color=INK, lw=1, ls="--")
a.text(prod.price_eur.median() * 1.08, a.get_ylim()[1] * 0.92, f"median {prod.price_eur.median():.0f} €", fontsize=8)
a.set(title="Price is log-normal (long right tail)", xlabel="price € (log scale)", ylabel="products")

a = ax[0, 1]
g = prod.category.value_counts().sort_values()
a.barh(g.index, g.values, color=BLUE, height=0.7)
a.set(title="Products per category", xlabel="products")
a.grid(axis="y", visible=False)

a = ax[0, 2]
r = prod.purchases.sort_values(ascending=False).to_numpy()
a.loglog(np.arange(1, len(r) + 1), np.maximum(r, 0.5), color=BLUE, lw=2)
top1 = r[: len(r) // 100].sum() / r.sum()
top10 = r[: len(r) // 10].sum() / r.sum()
gini = 1 - 2 * np.trapezoid(np.cumsum(np.sort(r)) / r.sum(), dx=1 / len(r))
a.text(0.04, 0.12, f"top 1% of products = {top1:.0%} of purchases\ntop 10% = {top10:.0%}\nGini = {gini:.2f}",
       transform=a.transAxes, fontsize=8)
a.set(title="Product popularity: heavy long tail", xlabel="product rank (log)", ylabel="organic purchases, 60 d (log)")
NUM["popularity"] = {"top1pct_share": top1, "top10pct_share": top10, "gini": gini,
                     "products_never_bought": int((prod.purchases == 0).sum())}

a = ax[1, 0]
a.hist(users.views, bins=np.logspace(0, np.log10(users.views.max()), 45), color=BLUE, edgecolor="#fcfcfb", lw=0.4)
a.set_xscale("log")
a.set(title="Views per shopper (60 days)", xlabel="views (log scale)", ylabel="shoppers")

a = ax[1, 1]
a.hist(users.purchases, bins=np.arange(0, 61) - 0.5, color=BLUE, edgecolor="#fcfcfb", lw=0.3)
a.set(title="Purchases per shopper (60 days)", xlabel="purchases", ylabel="shoppers")

a = ax[1, 2]
h = seg.groupby("n_recent").n.sum() / seg.n.sum()
lv = lr.groupby("n_recent").n.sum() / lr.n.sum()
x = np.arange(7)
a.bar(x - 0.2, 100 * h.reindex(x).fillna(0), 0.38, color=BLUE, label="history (old carousel)")
a.bar(x + 0.2, 100 * lv.reindex(x).fillna(0), 0.38, color=ORANGE, label="live requests (practice)")
a.set(title="Recent views in the request: live = history", xlabel="length(recent_views)", ylabel="% of requests")
a.set_xticks(x)
a.legend()
a.grid(axis="x", visible=False)
save(fig, "01_univariate", "1 · Univariate distributions")
NUM["users"] = {"n": len(users), "views_median": float(users.views.median()), "views_p99": float(users.views.quantile(0.99)),
                "purchases_median": float(users.purchases.median()), "zero_purchases": float((users.purchases == 0).mean())}
NUM["live"] = {"new_user_share": float(lr[lr.is_new_user == True].n.sum() / lr.n.sum()),  # noqa: E712
               "home_share": float(lr[lr.page == "home"].n.sum() / lr.n.sum())}

# ---------------------------------------------------------------------------------------------------------
# 2. OUTLIERS
# ---------------------------------------------------------------------------------------------------------
fig, ax = plt.subplots(1, 3, figsize=(15, 4.9))
a = ax[0]
order = prod.groupby("category").price_eur.median().sort_values().index
a.boxplot([np.log10(prod.price_eur[prod.category == c]) for c in order], vert=False, tick_labels=order, widths=0.6,
          patch_artist=True, boxprops=dict(facecolor="#b7d3f6", edgecolor=BLUE), medianprops=dict(color=INK, lw=1.4),
          whiskerprops=dict(color=BLUE), capprops=dict(color=BLUE),
          flierprops=dict(marker="o", ms=3, mfc=ORANGE, mec="none", alpha=0.7))
ticks = [2, 5, 10, 20, 50, 100, 200, 500]
a.set_xticks(np.log10(ticks), ticks)
a.set(title="Price by category (orange = Tukey outliers)", xlabel="price € (log scale)")
lp = np.log10(prod.price_eur)
q1, q3 = lp.quantile([0.25, 0.75])
n_price_out = int(((lp > q3 + 1.5 * (q3 - q1)) | (lp < q1 - 1.5 * (q3 - q1))).sum())

a = ax[1]
X = np.column_stack([np.log1p(prod.views), np.log1p(prod.purchases), np.log(prod.price_eur), prod.cart_rate, prod.buy_rate])
iso = IsolationForest(contamination=0.02, random_state=0).fit_predict(StandardScaler().fit_transform(X)) == -1
a.scatter(prod.views[~iso], prod.purchases[~iso] + 1, s=6, c=BLUE, alpha=0.35, lw=0, label="product")
a.scatter(prod.views[iso], prod.purchases[iso] + 1, s=14, c=ORANGE, lw=0, label="Isolation Forest outlier (2%)")
for j, (_, t) in enumerate(prod.nlargest(3, "purchases").iterrows()):
    a.annotate(f"{t.product_id} · {t.price_eur:.0f} €", (t.views, t.purchases + 1), fontsize=7, xytext=(-150, -6 - 16 * j),
               textcoords="offset points", color=INK2, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.5))
a.set(xscale="log", yscale="log", title="Products: views vs purchases", xlabel="organic views (log)", ylabel="purchases + 1 (log)")
a.legend(loc="lower right")

a = ax[2]
lz = np.log1p(users.views)
z = 0.6745 * (lz - lz.median()) / (lz - lz.median()).abs().median()
uo = z.abs() > 3.5
a.scatter(users.views[~uo], users.purchases[~uo] + 1, s=4, c=BLUE, alpha=0.2, lw=0, label="shopper")
a.scatter(users.views[uo], users.purchases[uo] + 1, s=10, c=ORANGE, lw=0, label="robust z-score > 3.5 (MAD)")
a.set(xscale="log", yscale="log", title="Shoppers: views vs purchases", xlabel="views (log)", ylabel="purchases + 1 (log)")
a.legend(loc="lower right")
save(fig, "02_outliers", "2 · Outliers")
NUM["outliers"] = {"price_tukey_log": n_price_out, "price_max": float(prod.price_eur.max()),
                   "products_isoforest": int(iso.sum()), "users_mad": int(uo.sum()),
                   "top_seller_share": float(prod.purchases.max() / prod.purchases.sum())}

# ---------------------------------------------------------------------------------------------------------
# 3. TIME
# ---------------------------------------------------------------------------------------------------------
evh["hour"] = pd.to_datetime(evh.hour.str[:19])
evh = evh[evh.hour < "2026-11-14 07:00"]
fig, ax = plt.subplots(2, 2, figsize=(14, 7.6))
a = ax[0, 0]
day = evh.assign(day=evh.hour.dt.floor("D")).pivot_table(index="day", columns="event_type", values="n", aggfunc="sum").iloc[1:-1]
idx = 100 * day / day.iloc[:7].mean()
for c, col in zip(["view", "add_to_cart", "purchase"], CAT):
    a.plot(idx.index, idx[c], color=col, lw=2, label=c)
a.set(title="Daily organic activity, indexed (first week = 100)", ylabel="index")
a.legend(ncol=3, loc="upper left")
a.tick_params(axis="x", rotation=30)

a = ax[0, 1]
hod = evh[evh.event_type == "purchase"].groupby(evh.hour.dt.hour).n.mean()
a.bar(hod.index, hod.values, color=BLUE, width=0.75)
a.set(title="Purchases per hour by hour of day (UTC)", xlabel="hour (UTC) — Barcelona = UTC+1", ylabel="purchases / hour")
a.grid(axis="x", visible=False)
NUM["time"] = {"peak_hour_utc": int(hod.idxmax()), "trough_hour_utc": int(hod.idxmin()), "peak_to_trough": float(hod.max() / hod.min())}

a = ax[1, 0]
sd["day"] = pd.to_datetime(sd.day)
sd = sd.sort_values("day").iloc[1:-1]
a.plot(sd.day, 100 * sd.buys / sd.n, color=BLUE, lw=2, label="conversion %")
a.plot(sd.day, 100 * sd.clicks / sd.n, color=ORANGE, lw=2, label="CTR %")
a.set(title="Old carousel, per day: stable (no drift in the log)", ylabel="% of requests")
a.set_ylim(0)
a.legend()
a.tick_params(axis="x", rotation=30)

a = ax[1, 1]
catd["week"] = (pd.to_datetime(catd.day) - pd.Timestamp("2026-09-15")).dt.days // 7
w = catd[catd.week < 8].pivot_table(index="category", columns="week", values="purchases", aggfunc="sum")
share = w / w.sum()
lift = share.div(share.mean(axis=1), axis=0)
lift.columns = [f"w{c + 1}" for c in lift.columns]
im = heat(a, lift, "Category share of purchases vs its own average (trend map)", cmap=DIV, center=1.0)
fig.colorbar(im, ax=a, shrink=0.8)
save(fig, "03_time", "3 · Time: seasonality and trends")
NUM["time"]["max_category_weekly_lift"] = float(lift.max().max())
NUM["time"]["min_category_weekly_lift"] = float(lift.min().min())

# ---------------------------------------------------------------------------------------------------------
# 4. CONTEXT → CONVERSION (all 2 M impressions of the old carousel)
# ---------------------------------------------------------------------------------------------------------
fig, ax = plt.subplots(2, 3, figsize=(15, 8))
spread = {}
for a, by, t, rot in [(ax[0, 0], "page", "by page", 0), (ax[0, 1], "n_recent", "by length(recent_views)", 0),
                      (ax[0, 2], "device", "by device", 0), (ax[1, 0], "region", "by region", 35),
                      (ax[1, 1], "hour", "by hour of day (UTC)", 0), (ax[1, 2], "dow", "by day of week (1 = Mon)", 0)]:
    order = seg.groupby(by).apply(lambda d: d.buys.sum() / d.n.sum()).sort_values(ascending=False).index if by in ("page", "region", "device") else None
    p = rate_bars(a, seg, by, title=f"Conversion % {t}", order=order, rot=rot)
    a.set_ylabel("purchases per 100 requests")
    spread[by] = float(p.max() / p.min())
    gg = seg.groupby(by)[["buys", "n"]].sum()
    pbar = gg.buys.sum() / gg.n.sum()
    spread[by + "_var_explained"] = float((gg.n * (gg.buys / gg.n - pbar) ** 2).sum() / gg.n.sum() / (pbar * (1 - pbar)))
save(fig, "04_context_conversion", "4 · Which request context converts? (old carousel, 2 M requests, 95% CI)")
NUM["context_spread_max_over_min"] = spread
pg = seg.groupby("page")[["n", "buys", "clicks", "revenue"]].sum()
NUM["page"] = {p: {"share_requests": float(r.n / pg.n.sum()), "share_purchases": float(r.buys / pg.buys.sum()),
                   "conversion_pct": float(100 * r.buys / r.n)} for p, r in pg.iterrows()}

fig, ax = plt.subplots(1, 3, figsize=(16, 5.2))
m = seg.pivot_table(index="region", columns="device", values=["buys", "n"], aggfunc="sum")
heat(ax[0], 100 * m["buys"] / m["n"], "Conversion % · region × device")
o = rc.pivot_table(index="region", columns="category", values="purchases", aggfunc="sum")
lift_rc = (o.div(o.sum(axis=1), axis=0)) / (o.sum() / o.sum().sum())
im = heat(ax[1], lift_rc, "Organic purchases · region × category lift", cmap=DIV, center=1.0)
o2 = rc.pivot_table(index="device", columns="category", values="purchases", aggfunc="sum")
lift_dc = (o2.div(o2.sum(axis=1), axis=0)) / (o2.sum() / o2.sum().sum())
heat(ax[2], lift_dc, "Organic purchases · device × category lift", cmap=DIV, center=1.0)
save(fig, "05_interactions", "5 · Interactions: region, device and category")
NUM["region_category_lift"] = {"max": float(lift_rc.max().max()), "min": float(lift_rc.min().min()),
                               "argmax": [str(x) for x in lift_rc.stack().idxmax()]}
NUM["device_category_lift"] = {"max": float(lift_dc.max().max()), "min": float(lift_dc.min().min())}

# ---------------------------------------------------------------------------------------------------------
# 5. ITEM LEVEL: explode the 10% sample into (request, slot) impressions
# ---------------------------------------------------------------------------------------------------------
ss = ss[ss.shown.map(len) == 10].reset_index(drop=True)
n = len(ss)
ss["ts"] = pd.to_datetime(ss.ts.str[:19])
shown = np.array(ss.shown.tolist())
rec = np.full((n, 6), "", dtype=object)
for i, r in enumerate(ss.recent):
    if len(r):
        rec[i, : len(r)] = r
ss["n_recent"] = (rec != "").sum(1)
ss["last"] = [r[-1] if len(r) else "" for r in ss.recent]
P = prod.set_index("product_id")
imp = pd.DataFrame({"req": np.repeat(np.arange(n), 10), "slot": np.tile(np.arange(1, 11), n), "item": shown.ravel(),
                    "prop": np.array(ss.propensity.tolist()).ravel()})
for c in ["user_id", "ts", "page", "device", "region", "n_recent", "last", "clicked", "purchased"]:
    imp[c] = np.repeat(ss[c].to_numpy(), 10)
imp["click"] = (imp.item == imp.clicked).astype(int)
imp["buy"] = (imp.item == imp.purchased).astype(int)
imp["in_recent"] = (shown[:, :, None] == rec[:, None, :]).any(-1).ravel().astype(int)
for c in ["category", "subcategory", "brand", "price_eur", "purchases", "views", "cart_rate", "buy_rate", "trend", "age_days"]:
    imp["i_" + c] = imp.item.map(P[c])
    if c in ("category", "subcategory", "brand", "price_eur"):
        imp["l_" + c] = imp["last"].map(P[c])
has = imp["last"] != ""
imp["same_cat"] = (has & (imp.i_category == imp.l_category)).astype(int)
imp["same_sub"] = (has & (imp.i_subcategory == imp.l_subcategory)).astype(int)
imp["same_brand"] = (has & (imp.i_brand == imp.l_brand)).astype(int)
imp["is_last"] = (has & (imp.item == imp["last"])).astype(int)
imp["price_ratio"] = np.log2(imp.i_price_eur / imp.l_price_eur)
imp["rel"] = np.select([~has, imp.same_sub == 1, imp.same_cat == 1], ["no recent view (home)", "same subcategory", "same category, other subcat."],
                       "other category")
# shopper features (computed on the whole 60 days: fine for description, leaky for a real model)
uv = ucat.pivot_table(index="user_id", columns="category", values="views", aggfunc="sum").fillna(0)
aff = uv.div(uv.sum(axis=1), axis=0).stack().rename("u_cat_affinity").reset_index()
imp = imp.merge(aff, left_on=["user_id", "i_category"], right_on=["user_id", "category"], how="left").drop(columns="category")
U = users.set_index("user_id")
imp["u_views"] = imp.user_id.map(U.views).fillna(0)
imp["u_buy_rate"] = imp.user_id.map(U.purchases / U.views).fillna(0)
imp["u_avg_price"] = imp.user_id.map(U.avg_view_price)
imp["u_known"] = imp.user_id.isin(U.index).astype(int)
imp["u_cat_affinity"] = imp.u_cat_affinity.fillna(0)
pur["ts"] = pd.to_datetime(pur.ts.str[:19])
first = pur.groupby(["user_id", "product_id"]).ts.min().rename("first_buy").reset_index()
imp = imp.merge(first, left_on=["user_id", "item"], right_on=["user_id", "product_id"], how="left").drop(columns="product_id")
imp["bought_before"] = (imp.first_buy < imp.ts).astype(int)
imp["hour"] = imp.ts.dt.hour
imp["price_vs_user"] = np.log2(imp.i_price_eur / imp.u_avg_price)

NUM["sample"] = {"requests": n, "impressions": len(imp), "ctr_per_impression": float(imp.click.mean()),
                 "buy_per_impression": float(imp.buy.mean())}
ctx = imp[has]
NUM["relation_mix_when_recent"] = {k: float(v) for k, v in ctx.rel.value_counts(normalize=True).items()}
NUM["relation_ctr_pct"] = {k: float(100 * v) for k, v in imp.groupby("rel").click.mean().items()}
NUM["relation_buy_pct"] = {k: float(100 * v) for k, v in imp.groupby("rel").buy.mean().items()}
NUM["in_recent"] = {"share": float(ctx.in_recent.mean()), "ctr_in": float(100 * ctx[ctx.in_recent == 1].click.mean()),
                    "ctr_out": float(100 * ctx[ctx.in_recent == 0].click.mean())}
NUM["satiation"] = {"share_impr_bought_before": float(imp.bought_before.mean()),
                    "ctr_bought_before": float(100 * imp[imp.bought_before == 1].click.mean()),
                    "ctr_not_bought": float(100 * imp[imp.bought_before == 0].click.mean()),
                    "buy_bought_before": float(100 * imp[imp.bought_before == 1].buy.mean()),
                    "buy_not_bought": float(100 * imp[imp.bought_before == 0].buy.mean())}
rep = pur.groupby(["user_id", "product_id"]).size()
NUM["satiation"]["organic_repeat_pair_share"] = float((rep > 1).mean())

fig, ax = plt.subplots(2, 3, figsize=(16, 8.6))
a = ax[0, 0]
for (k, d), col in zip(imp.groupby("rel"), [CAT[3], CAT[1], CAT[2], CAT[0]]):
    s = d.groupby("slot").click.mean() * 100
    a.plot(s.index, s.values, marker="o", ms=4, lw=2, color=col, label=k)
a.set(title="CTR per slot, by relation to the last viewed product", xlabel="slot", ylabel="clicks per 100 impressions")
a.set_xticks(range(1, 11))
a.legend()
sl = imp.groupby("slot").click.mean()
NUM["slot_ctr_ratio_1_vs_10"] = float(sl[1] / sl[10])

a = ax[0, 1]
ctx2 = ctx.assign(aff_bin=pd.qcut(ctx.u_cat_affinity, 8, duplicates="drop"))
s = ctx2.groupby("aff_bin", observed=True).agg(x=("u_cat_affinity", "mean"), ctr=("click", "mean"), buy=("buy", "mean"))
a.plot(s.x, 100 * s.ctr, marker="o", ms=4, lw=2, color=BLUE, label="click")
a.plot(s.x, 100 * s.buy, marker="o", ms=4, lw=2, color=ORANGE, label="purchase")
a.set(title="Shopper's affinity for the item's category", xlabel="share of the shopper's past views in that category",
      ylabel="per 100 impressions")
a.legend()
NUM["affinity_ctr_top_vs_bottom"] = float(s.ctr.iloc[-1] / s.ctr.iloc[0])

a = ax[0, 2]
ctx2 = ctx.assign(pb=pd.qcut(ctx.i_price_eur, 10, duplicates="drop"))
s = ctx2.groupby("pb", observed=True).agg(x=("i_price_eur", "median"), ctr=("click", "mean"), buy=("buy", "mean"),
                                           cvr=("buy", "sum"), clicks=("click", "sum"))
ck = imp[imp.click == 1]
ck = ck.assign(pb=pd.qcut(ck.i_price_eur, 8, duplicates="drop"))
s2 = ck.groupby("pb", observed=True).agg(x=("i_price_eur", "median"), n=("buy", "size"), buy=("buy", "sum"))
p, lo, hi = wilson(s2.buy, s2.n)
a.errorbar(s2.x, 100 * p, yerr=[100 * (p - lo), 100 * (hi - p)], color=BLUE, marker="o", ms=4, lw=2, ecolor=INK2, elinewidth=0.9, capsize=2)
a.set(xscale="log", title="After the click: share of clicks that end in a purchase,\nby price of the clicked item",
      xlabel="price of the clicked item € (octiles, log)", ylabel="% of clicks that buy")
a.set_ylim(0)
a.set_xticks([2, 5, 10, 20, 50, 100], [2, 5, 10, 20, 50, 100])
NUM["price"] = {"buy_given_click_by_price_octile": {f"{x:.0f}€": float(100 * v) for x, v in zip(s2.x, p)},
                "ctr_cheapest_vs_priciest_decile": float(s.ctr.iloc[0] / s.ctr.iloc[-1])}

a = ax[1, 0]
ctx2 = ctx.assign(pb=pd.qcut(ctx.i_purchases, 10, duplicates="drop"))
s = ctx2.groupby("pb", observed=True).agg(x=("i_purchases", "median"), ctr=("click", "mean"), buy=("buy", "mean"))
a.plot(s.x, 100 * s.ctr, marker="o", ms=4, lw=2, color=BLUE, label="click")
a.plot(s.x, 100 * s.buy, marker="o", ms=4, lw=2, color=ORANGE, label="purchase")
a.set(xscale="log", title="Item popularity (organic purchases, 60 d)", xlabel="item purchases (deciles, log)", ylabel="per 100 impressions")
a.set_xticks([200, 500, 1000, 2000, 5000], [200, 500, 1000, 2000, 5000])
a.minorticks_off()
a.legend()

a = ax[1, 1]
k = ctx.groupby("req").agg(m=("same_sub", "sum"), buy=("buy", "max"), click=("click", "max"))
s = k.groupby("m").agg(n=("buy", "size"), buy=("buy", "sum"), click=("click", "sum"))
s = s[s.n >= 300]
p, lo, hi = wilson(s.buy, s.n)
a.bar(s.index, 100 * p, color=BLUE, width=0.72)
a.errorbar(s.index, 100 * p, yerr=[100 * (p - lo), 100 * (hi - p)], fmt="none", ecolor=INK2, lw=0.9, capsize=2)
a.set(title="Request conversion vs how many of the 10 items share\nthe last view's subcategory", xlabel="items in the same subcategory",
      ylabel="purchases per 100 requests")
a.grid(axis="x", visible=False)
NUM["same_sub_count_conversion"] = {int(i): float(100 * v) for i, v in zip(s.index, p)}

a = ax[1, 2]
lab = ["not bought before", "already bought"]
v1 = [NUM["satiation"]["ctr_not_bought"], NUM["satiation"]["ctr_bought_before"]]
v2 = [NUM["satiation"]["buy_not_bought"], NUM["satiation"]["buy_bought_before"]]
x = np.arange(2)
a.bar(x - 0.2, v1, 0.38, color=BLUE, label="click")
a.bar(x + 0.2, v2, 0.38, color=ORANGE, label="purchase")
a.set_xticks(x, lab)
a.set(title="Satiation: items the shopper already bought", ylabel="per 100 impressions")
a.legend()
a.grid(axis="x", visible=False)
save(fig, "06_item_level", "6 · What makes one shown item get clicked and bought? (200 k requests = 2 M impressions)")

# ---------------------------------------------------------------------------------------------------------
# 6. PRODUCT SPACE: correlations + PCA
# ---------------------------------------------------------------------------------------------------------
pf = pd.DataFrame({"log price": np.log(prod.price_eur), "log views": np.log1p(prod.views), "log purchases": np.log1p(prod.purchases),
                   "cart rate": prod.cart_rate, "buy | cart": prod.buy_rate, "view→buy": prod.view_to_buy,
                   "trend (last/first wk)": prod.trend, "age (days)": prod.age_days}).fillna(0)
Z = StandardScaler().fit_transform(pf)
pca = PCA().fit(Z)
T = pca.transform(Z)
fig, ax = plt.subplots(1, 3, figsize=(17, 5.4))
im = heat(ax[0], pf.corr(method="spearman"), "Spearman correlation between product features", cmap=DIV, center=0.0)
a = ax[1]
ev = pca.explained_variance_ratio_
a.bar(range(1, len(ev) + 1), 100 * ev, color=BLUE, width=0.7)
a.plot(range(1, len(ev) + 1), 100 * np.cumsum(ev), color=INK, marker="o", ms=4, lw=1.5)
a.set(title="PCA scree: variance explained (line = cumulative)", xlabel="principal component", ylabel="% variance")
a.grid(axis="x", visible=False)
a = ax[2]
sc = a.scatter(T[:, 0], T[:, 1], c=np.log10(prod.price_eur), cmap=SEQ, s=7, lw=0, alpha=0.8)
bundle = ["log views", "log purchases", "cart rate", "view→buy"]  # r > 0.7 with each other: one label for the four
for j, name in enumerate(pf.columns):
    vx, vy = pca.components_[0, j] * 6, pca.components_[1, j] * 6
    a.annotate("", xy=(vx, vy), xytext=(0, 0), arrowprops=dict(arrowstyle="->", color=INK, lw=0.9))
    if name not in bundle:
        a.text(vx * 1.15, vy * 1.15, name, fontsize=8, ha="center", va="center", color=INK,
               bbox=dict(boxstyle="round,pad=0.15", fc="#fcfcfb", ec="none", alpha=0.85))
bx = pca.components_[:2, [list(pf.columns).index(b) for b in bundle]].mean(axis=1) * 6
a.text(bx[0] * 1.2 + 2.6, bx[1] * 1.2, "popularity\n(views, carts, purchases)", fontsize=8, ha="center", va="center", color=INK,
       bbox=dict(boxstyle="round,pad=0.15", fc="#fcfcfb", ec="none", alpha=0.85))
cb = fig.colorbar(sc, ax=a, shrink=0.8)
cb.set_label("log10 price €")
a.set(title="Products on PC1–PC2 (biplot)", xlabel=f"PC1 ({ev[0]:.0%})", ylabel=f"PC2 ({ev[1]:.0%})")
save(fig, "07_product_pca", "7 · Product space: correlations and PCA")
NUM["product_pca"] = {"explained": [float(x) for x in ev[:4]],
                      "pc1_loadings": {c: float(v) for c, v in zip(pf.columns, pca.components_[0])},
                      "pc2_loadings": {c: float(v) for c, v in zip(pf.columns, pca.components_[1])},
                      "spearman_price_vs_purchases": float(pf.corr(method="spearman").loc["log price", "log purchases"]),
                      "spearman_price_vs_viewbuy": float(pf.corr(method="spearman").loc["log price", "view→buy"])}

# ---------------------------------------------------------------------------------------------------------
# 7. SHOPPER SPACE: PCA + K-means + UMAP
# ---------------------------------------------------------------------------------------------------------
sh = uv.div(uv.sum(axis=1), axis=0)
ent = -(sh * np.log(sh.where(sh > 0, 1))).sum(axis=1) / np.log(10)
uf = pd.DataFrame({"log views": np.log1p(U.views), "views / session": U.views / U.sessions, "cart rate": U.carts / U.views.clip(lower=1),
                   "buy rate": U.purchases / U.views.clip(lower=1), "log avg price viewed": np.log(U.avg_view_price),
                   "category entropy": ent}).join(sh.add_prefix("share · ")).dropna()
Zu = StandardScaler().fit_transform(uf)
pu = PCA(random_state=0).fit(Zu)
Tu = pu.transform(Zu)
keep = int(np.searchsorted(np.cumsum(pu.explained_variance_ratio_), 0.9) + 1)
sub = RNG.choice(len(uf), 12000, replace=False)
sil = {}
for kk in range(2, 13):
    lab = KMeans(kk, n_init=4, random_state=0).fit_predict(Tu[sub, :keep])
    sil[kk] = float(silhouette_score(Tu[sub, :keep], lab, sample_size=6000, random_state=0))
best = max(sil, key=sil.get)
km = KMeans(best, n_init=10, random_state=0).fit(Tu[:, :keep])
uf["cluster"] = km.labels_
order = uf.cluster.value_counts().index
relabel = {old: new for new, old in enumerate(order)}
uf["cluster"] = uf.cluster.map(relabel)
colors = [CAT[c] if c < 8 else MUTED for c in range(best)]
import umap  # noqa: E402

emb = umap.UMAP(n_neighbors=30, min_dist=0.15, random_state=0).fit_transform(Tu[sub, :keep])
prof = uf.groupby("cluster").mean()
zprof = (prof - uf.drop(columns="cluster").mean()) / uf.drop(columns="cluster").std()
names = {}
for c, row in zprof.iterrows():
    top = row.sort_values(ascending=False).index[0].replace("share · ", "")
    names[c] = f"C{c} · {top}"
sess_c = ss.assign(cluster=ss.user_id.map(uf.cluster)).dropna(subset=["cluster"])
sess_c["buy"] = (sess_c.purchased != "").astype(int)
sess_c["click"] = (sess_c.clicked != "").astype(int)
cc = sess_c[sess_c.page != "home"].groupby("cluster").agg(n=("buy", "size"), buy=("buy", "sum"), click=("click", "sum"))

fig, ax = plt.subplots(2, 3, figsize=(17, 10))
a = ax[0, 0]
a.plot(list(sil), list(sil.values()), marker="o", color=BLUE, lw=2)
a.axvline(best, color=INK, ls="--", lw=1)
a.set(title=f"Choosing k: silhouette peaks at k = {best}", xlabel="k (K-means on PCA scores)", ylabel="silhouette")
a = ax[0, 1]
cl = uf.cluster.to_numpy()[sub]
for c in range(best):
    mk = cl == c
    a.scatter(Tu[sub][mk, 0], Tu[sub][mk, 1], s=5, lw=0, alpha=0.6, color=colors[c], label=names[c])
a.set(title="Shoppers on PC1–PC2 (linear view)", xlabel=f"PC1 ({pu.explained_variance_ratio_[0]:.0%})",
      ylabel=f"PC2 ({pu.explained_variance_ratio_[1]:.0%})")
a = ax[0, 2]
for c in range(best):
    mk = cl == c
    a.scatter(emb[mk, 0], emb[mk, 1], s=5, lw=0, alpha=0.6, color=colors[c], label=names[c])
a.set(title="UMAP of the same shoppers (non-linear view)", xlabel="UMAP 1", ylabel="UMAP 2")
a.legend(markerscale=3, fontsize=7, ncol=2, loc="best")
a = ax[1, 0]
zp = zprof.copy()
zp.index = [names[c] for c in zp.index]
zp.columns = [c.replace("share · ", "% ") for c in zp.columns]
im = heat(a, zp.T, "Cluster profiles (z-score vs all shoppers)", cmap=DIV, center=0.0, fmt="{:.1f}")
a.tick_params(axis="x", labelsize=7)
a = ax[1, 1]
size = uf.cluster.value_counts().sort_index()
topshare = sh.max(axis=1).reindex(uf.index).to_numpy()[sub]
sc = a.scatter(emb[:, 0], emb[:, 1], c=topshare, cmap=SEQ, s=5, lw=0, alpha=0.8, vmin=0.1, vmax=0.7)
cb = fig.colorbar(sc, ax=a, shrink=0.8)
cb.set_label("share of views in the favourite category")
a.set(title="Same UMAP: each arm is a favourite category", xlabel="UMAP 1", ylabel="UMAP 2")
fav = sh.idxmax(axis=1).reindex(uf.index).to_numpy()[sub]
for c in sh.columns:  # label each arm at the centroid of its most specialised shoppers
    mk = (fav == c) & (topshare > np.quantile(topshare[fav == c], 0.8))
    if mk.sum() > 5:
        a.text(np.median(emb[mk, 0]), np.median(emb[mk, 1]), c, fontsize=7, ha="center", va="center", color=INK,
               bbox=dict(boxstyle="round,pad=0.15", fc="#fcfcfb", ec="none", alpha=0.8))
a = ax[1, 2]
p, lo, hi = wilson(cc.buy, cc.n)
a.bar(range(len(cc)), 100 * p, color=[colors[int(c)] for c in cc.index], width=0.72)
a.errorbar(range(len(cc)), 100 * p, yerr=[100 * (p - lo), 100 * (hi - p)], fmt="none", ecolor=INK2, lw=0.9, capsize=2)
a.set_xticks(range(len(cc)), [f"C{int(c)}" for c in cc.index])
a.set(title="Carousel conversion by cluster (non-home pages)", ylabel="purchases per 100 requests")
a.grid(axis="x", visible=False)
save(fig, "08_shopper_clusters", "8 · Shopper space: PCA, K-means and UMAP")
NUM["shopper_clusters"] = {"k": best, "silhouette": sil, "pca_components_for_90pct": keep,
                           "pca_explained_first3": [float(x) for x in pu.explained_variance_ratio_[:3]],
                           "names": names, "size_pct": {int(k): float(100 * v / size.sum()) for k, v in size.items()},
                           "conversion_pct": {int(k): float(100 * v) for k, v in zip(cc.index, p)},
                           "median_entropy": float(ent.median()),
                           "median_top_category_share": float(sh.max(axis=1).median())}

half = pd.Timestamp("2026-10-15 07:00")
late = ss[(ss.ts >= half) & (ss.page != "home")].copy()
late["early_buys"] = late.user_id.map(pur[pur.ts < half].groupby("user_id").size()).fillna(0)
late["bin"] = pd.cut(late.early_buys, [-1, 0, 2, 5, 10, 1e9], labels=["0", "1-2", "3-5", "6-10", "11+"])
late["buy"] = (late.purchased != "").astype(int)
gb = late.groupby("bin", observed=True).buy.agg(["size", "sum"])
NUM["buyer_persistence"] = {str(k): {"n": int(r["size"]), "conversion_pct": float(100 * r["sum"] / r["size"])} for k, r in gb.iterrows()}

# ---------------------------------------------------------------------------------------------------------
# 8. WHAT MATTERS MOST: gradient boosting + SHAP on impressions
# ---------------------------------------------------------------------------------------------------------
feats = ["slot", "page", "device", "region", "n_recent", "hour", "same_sub", "same_brand", "is_last", "in_recent",
         "price_ratio", "i_price_eur", "i_purchases", "i_cart_rate", "i_buy_rate", "i_trend", "i_age_days", "i_category",
         "u_cat_affinity", "u_views", "u_buy_rate", "price_vs_user", "bought_before"]
pretty = {"slot": "slot (position)", "page": "page", "device": "device", "region": "region", "n_recent": "length(recent_views)",
          "hour": "hour of day", "same_sub": "same subcategory as last view", "same_brand": "same brand as last view",
          "is_last": "is the last viewed product", "in_recent": "is in recent_views", "price_ratio": "price vs last viewed",
          "i_price_eur": "item price", "i_purchases": "item popularity (purchases)", "i_cart_rate": "item cart rate",
          "i_buy_rate": "item buy|cart rate", "i_trend": "item trend", "i_age_days": "item age", "i_category": "item category",
          "u_cat_affinity": "shopper affinity for item category", "u_views": "shopper activity (views)",
          "u_buy_rate": "shopper buy rate", "price_vs_user": "price vs shopper's usual price",
          "bought_before": "shopper already bought it"}
Xall = imp[feats].copy()
for c in ["page", "device", "region", "i_category"]:
    Xall[c] = Xall[c].astype("category")
cut = imp.ts.quantile(0.8)
is_click = (imp.click == 1).to_numpy()
fig, ax = plt.subplots(1, 2, figsize=(16, 7.2))
NUM["model"] = {}
specs = [("click", "P(click) per impression", np.ones(len(imp), bool), BLUE,
          dict(n_estimators=120, learning_rate=0.1, num_leaves=31, min_child_samples=200, subsample=0.5, max_bin=63)),
         ("buy", "P(purchase | click)", is_click, ORANGE,
          dict(n_estimators=150, learning_rate=0.03, num_leaves=8, min_child_samples=60, subsample=0.8, reg_lambda=5.0))]
for a, (target, label, rows, col, params) in zip(ax, specs):
    tr, te = rows & (imp.ts <= cut).to_numpy(), rows & (imp.ts > cut).to_numpy()
    m = lgb.LGBMClassifier(subsample_freq=1, colsample_bytree=0.8, verbose=-1, random_state=0, **params)
    m.fit(Xall[tr], imp[target][tr])
    auc = roc_auc_score(imp[target][te], m.predict_proba(Xall[te])[:, 1])
    samp = Xall[te].sample(min(60_000, int(te.sum())), random_state=0)
    shap = m.booster_.predict(samp, pred_contrib=True)[:, :-1]
    imp_s = pd.Series(np.abs(shap).mean(0), index=[pretty[f] for f in feats]).sort_values()
    a.barh(imp_s.index, imp_s.values, color=col, height=0.72)
    a.set(title=f"{label} · AUC {auc:.3f} on the last 12 days",
          xlabel=f"mean |SHAP| (log-odds) · trained on {int(tr.sum()):,} rows")
    a.grid(axis="y", visible=False)
    # signed effect of the yes/no features: mean SHAP when the flag is on minus when it is off (log-odds)
    signed = {pretty[f]: float(shap[samp[f].to_numpy() == 1, feats.index(f)].mean() - shap[samp[f].to_numpy() == 0, feats.index(f)].mean())
              for f in ["same_sub", "same_brand", "is_last", "in_recent", "bought_before"]}
    NUM["model"][target] = {"auc": float(auc), "train_rows": int(tr.sum()), "signed_effect_logodds": signed,
                            "shap": {k: float(v) for k, v in imp_s.sort_values(ascending=False).items()}}
NUM["model"]["click"]["auc_slot_only"] = float(roc_auc_score(imp.click[(imp.ts > cut).to_numpy()], -imp.slot[(imp.ts > cut).to_numpy()]))
save(fig, "09_feature_importance", "9 · What matters most? Gradient boosting + SHAP (click, then purchase given click)")

# live baseline feedback (fallback = global best sellers) as a sanity check of the same structure
lf2 = lf.groupby("page")[["n", "clicks", "buys", "revenue"]].sum()
NUM["live_feedback_by_page"] = {p: {"n": int(r.n), "conversion_pct": float(100 * r.buys / r.n), "ctr_pct": float(100 * r.clicks / r.n)}
                                for p, r in lf2.iterrows()}
lf3 = lf.groupby("is_new_user")[["n", "buys"]].sum()
NUM["live_feedback_by_new_user"] = {str(k): {"n": int(r.n), "conversion_pct": float(100 * r.buys / r.n)} for k, r in lf3.iterrows()}

(HERE / "numbers.json").write_text(json.dumps(NUM, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print(json.dumps(NUM, indent=1, ensure_ascii=False, default=str))
