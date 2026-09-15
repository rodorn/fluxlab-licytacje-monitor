"""Scoring okazji dla licytacji ruchomosci.

Wskaznik okazji = cena_wywolawcza / wartosc_szacunkowa.
Im nizszy, tym atrakcyjniejsza cena wzgledem wartosci.
Flaga HOT gdy wskaznik < progu (domyslnie 0.60).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .scraper import Auction

HOT_THRESHOLD = 0.60


@dataclass
class ScoredAuction:
    auction: Auction
    ratio: Optional[float]
    hot: bool


def opportunity_ratio(
    cena_wywolawcza: Optional[float],
    wartosc_szacunkowa: Optional[float],
) -> Optional[float]:
    """Zwraca stosunek ceny wywolawczej do wartosci szacunkowej.

    None gdy brak danych lub wartosc szacunkowa <= 0.
    """
    if cena_wywolawcza is None or wartosc_szacunkowa is None:
        return None
    if wartosc_szacunkowa <= 0:
        return None
    return cena_wywolawcza / wartosc_szacunkowa


def is_hot(ratio: Optional[float], threshold: float = HOT_THRESHOLD) -> bool:
    """True gdy wskaznik istnieje i jest ponizej progu."""
    if ratio is None:
        return False
    return ratio < threshold


def score(auction: Auction, threshold: float = HOT_THRESHOLD) -> ScoredAuction:
    ratio = opportunity_ratio(auction.cena_wywolawcza, auction.wartosc_szacunkowa)
    return ScoredAuction(auction=auction, ratio=ratio, hot=is_hot(ratio, threshold))


def score_all(
    auctions: List[Auction], threshold: float = HOT_THRESHOLD
) -> List[ScoredAuction]:
    return [score(a, threshold) for a in auctions]


def hot_only(scored: List[ScoredAuction]) -> List[ScoredAuction]:
    return [s for s in scored if s.hot]
