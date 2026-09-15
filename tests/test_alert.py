import csv

from src.alert import export_csv, send_discord
from src.scoring import score_all
from src.scraper import demo_auctions


def _scored():
    return score_all(demo_auctions())


def test_export_csv(tmp_path):
    path = tmp_path / "out" / "wyniki.csv"
    export_csv(_scored(), str(path))
    assert path.exists()
    with open(path, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 3
    assert {"tytul", "wskaznik_okazji", "hot", "url"} <= set(rows[0].keys())
    # koparka JCB 78000/150000 = 0.52 -> HOT
    koparka = [r for r in rows if "JCB" in r["tytul"]][0]
    assert koparka["hot"] == "HOT"
    assert koparka["wskaznik_okazji"] == "0.52"


def test_discord_noop_without_url(monkeypatch):
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    assert send_discord(_scored()) is False


def test_discord_noop_without_items():
    assert send_discord([], webhook_url="https://example.com/hook") is False
