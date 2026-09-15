"""Spina caly pipeline: scrape (lub demo) -> scoring -> filtr HOT -> alert/CSV.

Uzycie:
    python run.py --demo                 # tryb demo (bez sieci)
    python run.py --category MOVABLE     # pobranie na zywo z portalu
    python run.py --live --province mazowieckie
    python run.py --threshold 0.5 --csv data/wyniki.csv

Alert Discord dziala tylko gdy ustawiono env DISCORD_WEBHOOK_URL.
"""

from __future__ import annotations

import argparse
import sys

from src import alert, scoring
from src.scraper import demo_auctions, fetch_listing

DEFAULT_CSV = "data/licytacje.csv"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="FluxLab monitor licytacji ruchomosci")
    p.add_argument("--demo", action="store_true", help="tryb demo bez sieci")
    p.add_argument("--live", action="store_true", help="pobierz na zywo z portalu")
    p.add_argument(
        "--category",
        default="MOVABLE",
        help="kategoria: MOVABLE (ruchomosci) lub REAL_ESTATE",
    )
    p.add_argument("--province", default=None, help="wojewodztwo (opcjonalne)")
    p.add_argument(
        "--threshold",
        type=float,
        default=scoring.HOT_THRESHOLD,
        help="prog HOT (domyslnie 0.60)",
    )
    p.add_argument("--csv", default=DEFAULT_CSV, help="sciezka pliku CSV")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    live = args.live and not args.demo
    if live:
        print(f"Pobieram listing na zywo (category={args.category})...")
        auctions = fetch_listing(main_category=args.category, province=args.province)
    else:
        print("Tryb demo: uzywam wbudowanego przykladu.")
        auctions = demo_auctions()

    print(f"Pobrano ogloszen: {len(auctions)}")

    scored = scoring.score_all(auctions, threshold=args.threshold)
    hot = scoring.hot_only(scored)
    print(f"Okazje HOT (wskaznik < {args.threshold:.0%}): {len(hot)}")

    csv_path = alert.export_csv(scored, args.csv)
    print(f"Zapisano CSV: {csv_path}")

    sent = alert.send_discord(hot)
    print(
        f"Alert Discord: {'wyslano' if sent else 'pominieto (brak URL lub brak HOT)'}"
    )

    if hot:
        print("\n--- Okazje HOT ---")
        for s in hot:
            a = s.auction
            print(
                f"[{s.ratio:.0%}] {a.tytul} | {a.cena_wywolawcza} / "
                f"{a.wartosc_szacunkowa} zl | {a.lokalizacja} | {a.data_licytacji}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
