from src.scraper import _parse_price, demo_auctions, parse_listing


def test_parse_price_variants():
    assert _parse_price("1500,00 zl") == 1500.0
    assert _parse_price("78 000,00 zl") == 78000.0
    assert _parse_price("1\xa0500,50 zł") == 1500.5
    assert _parse_price("") is None
    assert _parse_price("brak") is None


def test_demo_parses_all_fields():
    auctions = demo_auctions()
    assert len(auctions) == 3

    opel = auctions[0]
    assert "Opel Astra" in opel.tytul
    assert opel.kategoria == "samochody osobowe"
    assert opel.cena_wywolawcza == 1500.0
    assert opel.wartosc_szacunkowa == 2000.0
    assert "Warszawa" in opel.lokalizacja
    assert "09.09.2026" in opel.data_licytacji
    assert opel.url.startswith("https://licytacje.komornik.pl/licytacje/")


def test_parse_primary_vs_secondary_price():
    koparka = demo_auctions()[1]
    # cena wywolawcza (primary) < wartosc szacunkowa (secondary)
    assert koparka.cena_wywolawcza == 78000.0
    assert koparka.wartosc_szacunkowa == 150000.0


def test_parse_empty_html():
    assert parse_listing("<html><body>nic</body></html>") == []
