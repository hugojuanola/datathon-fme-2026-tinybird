"""The ranking policy: 10 products for one shopper.

v1 is a transparent rule cascade, each tier justified by a measurement (see docs/findings.md):

    1. recent      products the shopper just viewed in this session (most recent first)
    2. cart        products the shopper carted but never bought (same category as the session first)
    3. fill        popular products; the arm decides from where:
                     sub   same subcategory as the last view, then same category, then global
                     cat   same category as the last view, then global
                     glob  global best sellers

Products the shopper already bought are never shown (satiation), and neither is anything out of
stock (one such product would invalidate the whole answer).
"""
from __future__ import annotations

import zlib

from reco.state import State

ARMS = ("sub", "cat", "glob")


def arm_of(request_id: str) -> str:
    """Deterministic A/B/C split on the request id, so every variant sees the same kind of traffic."""
    return ARMS[zlib.crc32(request_id.encode()) % len(ARMS)]


def recommend(state: State, user: str, recent_views: list[str], arm: str) -> tuple[list[str], list[str]]:
    """Return (10 product ids, the tier each one came from)."""
    products, unavailable = state.products, state.unavailable
    bought = state.purchased.get(user, ())
    items: list[str] = []
    tiers: list[str] = []
    chosen: set[str] = set()

    def take(candidates, tier: str, limit: int = 10) -> None:
        for p in candidates:
            if len(items) >= limit:
                return
            if p not in chosen and p not in unavailable and p not in bought and p in products:
                chosen.add(p)
                items.append(p)
                tiers.append(tier)

    take(reversed(recent_views), "recent")

    last = next((products[p] for p in reversed(recent_views) if p in products), None)
    carted = state.carted.get(user)
    if carted:
        newest_first = sorted(list(carted.items()), key=lambda kv: -kv[1])
        if last:
            take((p for p, _ in newest_first if p in products and products[p].category == last.category), "cart")
        take((p for p, _ in newest_first), "cart")

    if last and arm == "sub":
        take(state.by_sub.get(last.subcategory, ()), "fill_sub")
    if last and arm in ("sub", "cat"):
        take(state.by_cat.get(last.category, ()), "fill_cat")
    take(state.best, "fill_glob")
    return items, tiers


def safe_list(state: State) -> list[str]:
    """Last resort: the in-stock best sellers (what the organisers' fallback would show)."""
    return [p for p in state.best if p not in state.unavailable][:10]


def is_valid(state: State, items: list[str]) -> bool:
    return (len(items) == 10 and len(set(items)) == 10
            and all(p in state.products and p not in state.unavailable for p in items))
