"""Alerty: webhook Discord + eksport CSV."""

from __future__ import annotations

import csv
import os
from typing import List, Optional

import requests

from .scoring import ScoredAuction

CSV_FIELDS = [
    "tytul",
    "kategoria",
    "cena_wywolawcza",
    "wartosc_szacunkowa",
    "wskaznik_okazji",
    "hot",
    "lokalizacja",
    "data_licytacji",
    "url",
]


def _row(s: ScoredAuction) -> dict:
    a = s.auction
    return {
        "tytul": a.tytul,
        "kategoria": a.kategoria,
        "cena_wywolawcza": a.cena_wywolawcza,
        "wartosc_szacunkowa": a.wartosc_szacunkowa,
        "wskaznik_okazji": round(s.ratio, 4) if s.ratio is not None else "",
        "hot": "HOT" if s.hot else "",
        "lokalizacja": a.lokalizacja,
        "data_licytacji": a.data_licytacji,
        "url": a.url,
    }


def export_csv(scored: List[ScoredAuction], path: str) -> str:
    """Zapisuje wyniki do pliku CSV. Zwraca sciezke."""
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for s in scored:
            writer.writerow(_row(s))
    return path


def _format_message(scored: List[ScoredAuction]) -> str:
    lines = ["**FluxLab / Monitor licytacji: nowe okazje HOT**", ""]
    for s in scored:
        a = s.auction
        pct = f"{s.ratio * 100:.0f}%" if s.ratio is not None else "brak"
        lines.append(
            f"- {a.tytul} ({a.kategoria}) | cena {a.cena_wywolawcza} zl "
            f"/ szac. {a.wartosc_szacunkowa} zl = {pct} | "
            f"{a.lokalizacja} | {a.data_licytacji}\n  {a.url}"
        )
    return "\n".join(lines)


def send_discord(
    scored: List[ScoredAuction],
    webhook_url: Optional[str] = None,
    timeout: int = 15,
) -> bool:
    """Wysyla alert na webhook Discord.

    URL brany z argumentu lub env DISCORD_WEBHOOK_URL.
    Gdy brak URL lub brak ogloszen: no-op, zwraca False.
    Zwraca True gdy wyslano.
    """
    url = webhook_url or os.environ.get("DISCORD_WEBHOOK_URL")
    if not url or not scored:
        return False
    content = _format_message(scored)
    # Discord limit 2000 znakow na wiadomosc.
    resp = requests.post(url, json={"content": content[:1990]}, timeout=timeout)
    resp.raise_for_status()
    return True
