from src.scoring import (
    HOT_THRESHOLD,
    is_hot,
    opportunity_ratio,
    score_all,
    hot_only,
)
from src.scraper import Auction


def _a(cena, szac):
    return Auction(
        tytul="t",
        kategoria="k",
        cena_wywolawcza=cena,
        wartosc_szacunkowa=szac,
        lokalizacja="l",
        data_licytacji="d",
        url="u",
    )


def test_ratio_basic():
    assert opportunity_ratio(1500, 2000) == 0.75
    assert opportunity_ratio(60, 100) == 0.60


def test_ratio_none_on_missing_or_zero():
    assert opportunity_ratio(None, 100) is None
    assert opportunity_ratio(100, None) is None
    assert opportunity_ratio(100, 0) is None
    assert opportunity_ratio(100, -5) is None


def test_hot_threshold_boundary():
    # dokladnie na progu -> NIE hot (warunek to <)
    assert is_hot(HOT_THRESHOLD) is False
    assert is_hot(0.599) is True
    assert is_hot(0.60) is False
    assert is_hot(0.61) is False
    assert is_hot(None) is False


def test_hot_custom_threshold():
    assert is_hot(0.45, threshold=0.5) is True
    assert is_hot(0.55, threshold=0.5) is False


def test_score_all_and_hot_only():
    auctions = [
        _a(78000, 150000),  # 0.52 -> HOT
        _a(1500, 2000),  # 0.75 -> nie
        _a(None, 2000),  # brak -> nie
    ]
    scored = score_all(auctions)
    assert [s.hot for s in scored] == [True, False, False]
    hot = hot_only(scored)
    assert len(hot) == 1
    assert hot[0].auction.cena_wywolawcza == 78000
