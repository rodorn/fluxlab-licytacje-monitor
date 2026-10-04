# Monitor licytacji komorniczych ruchomosci

> Monitorowanie serwisów i pobieranie danych na zamówienie: [fluxlab.pl/scraping-danych](https://fluxlab.pl/scraping-danych?utm_source=github&utm_campaign=fluxlab-licytacje-monitor)

Monitor publicznych licytacji komorniczych i syndyckich ruchomosci
(maszyny budowlane, maszyny rolnicze, pojazdy) z oficjalnego portalu
Krajowej Rady Komorniczej, ze scoringiem okazji i alertem.

Wzorzec: scraper, ocena, alert.

## Jak dziala

1. `src/scraper.py` pobiera listing z portalu
   `https://licytacje.komornik.pl` (renderowany po stronie serwera,
   parser HTML). Pola: tytul, kategoria, cena wywolawcza, wartosc
   szacunkowa, lokalizacja, data licytacji, url. Throttle, timeout,
   user-agent, retry z backoffem.
2. `src/scoring.py` liczy wskaznik okazji
   `cena_wywolawcza / wartosc_szacunkowa`. Flaga HOT gdy wskaznik jest
   ponizej progu (domyslnie 60%).
3. `src/alert.py` wysyla alert na webhook Discord (env
   `DISCORD_WEBHOOK_URL`, no-op gdy brak) oraz eksportuje wyniki do CSV.
4. `run.py` spina calosc: scrape (lub demo), scoring, filtr HOT,
   alert i CSV.

## Instalacja

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Uruchomienie

Tryb demo (bez sieci, wbudowany przyklad):

```bash
python run.py --demo
```

Pobranie na zywo z portalu (tylko dane publiczne):

```bash
python run.py --live --category MOVABLE
python run.py --live --province mazowieckie --threshold 0.5
```

Alert Discord wlacza sie po ustawieniu zmiennej srodowiskowej:

```bash
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
python run.py --live
```

## Testy

```bash
pytest -q
```

## Zasady i ToS

Projekt korzysta wylacznie z publicznie dostepnych ogloszen (bez
logowania), stosuje throttle miedzy zapytaniami, rozsadny user-agent,
timeout i retry. Szanuj regulamin zrodla i lokalne prawo. Narzedzie ma
charakter informacyjny i nie stanowi porady inwestycyjnej ani prawnej.

## Konfiguracja

| Zmienna / flaga       | Znaczenie                               |
| --------------------- | --------------------------------------- |
| `DISCORD_WEBHOOK_URL` | webhook Discord do alertow (opcjonalny) |
| `--demo`              | tryb offline na wbudowanym przykladzie  |
| `--live`              | pobranie na zywo z portalu              |
| `--category`          | MOVABLE (ruchomosci) lub REAL_ESTATE    |
| `--province`          | filtr wojewodztwa                       |
| `--threshold`         | prog HOT (domyslnie 0.60)               |
| `--csv`               | sciezka wyjsciowego CSV                 |

---

Made by [FluxLab](https://fluxlab.pl) . Automatyzacja procesow
biznesowych i wdrozenia AI dla malych firm.
