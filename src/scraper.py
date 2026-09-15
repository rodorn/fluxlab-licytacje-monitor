"""Scraper publicznych ogloszen licytacji komorniczych ruchomosci.

Zrodlo: https://licytacje.komornik.pl (oficjalny portal Krajowej Rady
Komorniczej). Strona jest renderowana po stronie serwera (SSR, Nuxt),
wiec listing ogloszen jest dostepny w zwyklym HTML i mozna go sparsowac.

Zasady szanowania ToS:
- tylko publicznie dostepne dane (listing bez logowania),
- throttle miedzy zapytaniami,
- rozsadny user-agent, timeout i retry z backoffem.
"""

from __future__ import annotations

import re
import time
from dataclasses import asdict, dataclass, field
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://licytacje.komornik.pl"
SEARCH_PATH = "/wyszukiwarka-licytacji"

DEFAULT_USER_AGENT = (
    "FluxLab-LicytacjeMonitor/1.0 (+https://fluxlab.pl; "
    "kontakt: kontakt@fluxlab.pl) requests"
)

# Domyslne parametry siatki bezpieczenstwa.
DEFAULT_TIMEOUT = 20
DEFAULT_THROTTLE = 1.5
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF = 2.0


@dataclass
class Auction:
    """Pojedyncze ogloszenie licytacji ruchomosci."""

    tytul: str
    kategoria: str
    cena_wywolawcza: Optional[float]
    wartosc_szacunkowa: Optional[float]
    lokalizacja: str
    data_licytacji: str
    url: str

    def as_dict(self) -> dict:
        return asdict(self)


def _parse_price(text: str) -> Optional[float]:
    """Zamienia napis typu '1 500,00 zl' na float 1500.0."""
    if not text:
        return None
    cleaned = text.replace("\xa0", " ")
    cleaned = re.sub(r"(zl|zł|PLN)", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.replace(" ", "").replace(".", "")
    cleaned = cleaned.replace(",", ".")
    m = re.search(r"-?\d+(?:\.\d+)?", cleaned)
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _card_price(card, primary: bool) -> Optional[float]:
    """Wyciaga cene z karty.

    W HTML portalu 'Cena wywolania' ma klase auction__price--primary,
    a 'Suma oszacowania' to zwykly auction__price (bez modyfikatora).
    """
    for node in card.select(".auction__price"):
        classes = node.get("class", [])
        is_primary = "auction__price--primary" in classes
        if is_primary == primary:
            return _parse_price(node.get_text(" ", strip=True))
    return None


def _card_text_by_label(card, label: str) -> str:
    """Znajduje wartosc wystepujaca po etykiecie (np. 'Poczatek:')."""
    full = card.get_text("\n", strip=True)
    lines = [l for l in full.split("\n") if l]
    for i, line in enumerate(lines):
        if line.lower().startswith(label.lower()):
            if i + 1 < len(lines):
                return lines[i + 1]
    return ""


def parse_listing(html: str) -> List[Auction]:
    """Parsuje HTML strony listingu i zwraca liste ogloszen.

    Parser jest odporny na obecnosc/brak poszczegolnych pol; brakujace
    pola sa uzupelniane wartoscia domyslna (pusta / None).
    """
    soup = BeautifulSoup(html, "html.parser")

    # Ikony (cds-icon) renderuja sie jako tekst ligatury (np. 'map_marker',
    # 'calendar_month'), ktory zasmiecalby pola. Usuwamy je przed parsowaniem.
    for icon in soup.select(".cds-icon"):
        icon.decompose()

    results: List[Auction] = []

    for card in soup.select(".auction"):
        link = card.find("a", href=re.compile(r"/licytacje/\d+"))
        if link is None and card.name == "a" and card.get("href"):
            link = card
        href = link.get("href") if link else ""
        if not href or "/licytacje/" not in href:
            continue
        url = href if href.startswith("http") else BASE_URL + href

        # Kategoria: chip w auction__tags. Pomijamy chipy statusu
        # (np. 'e-licytacja w toku') i bierzemy pierwszy pozostaly.
        kategoria = ""
        chips = card.select(".auction__tags .cds-chip__content-wrapper")
        for chip in chips:
            txt = _clean(chip.get_text(" ", strip=True))
            if txt and "licytacj" not in txt.lower():
                kategoria = txt
                break
        if not kategoria:
            tags = card.select_one(".auction__tags")
            if tags is not None:
                kategoria = _clean(tags.get_text(" ", strip=True))

        # Tytul: dedykowany element auction__title, potem naglowek, link, slug.
        tytul = ""
        title_el = card.select_one(".auction__title")
        if title_el is None:
            title_el = card.select_one(".auction__content h2, .auction__content h3")
        if title_el is not None:
            tytul = _clean(title_el.get_text(" ", strip=True))
        if not tytul and link is not None:
            tytul = _clean(link.get_text(" ", strip=True))
        if not tytul:
            slug = href.rstrip("/").split("/")[-1]
            tytul = slug.replace("-", " ")

        # Lokalizacja: adres to ostatni auction__attribute w wierszu lokalizacji
        # (pierwszy to wojewodztwo). Fallback: caly tekst wiersza.
        lokalizacja = ""
        loc = card.select_one(".auction__row--location")
        if loc is not None:
            attrs = loc.select(".auction__attribute")
            if attrs:
                lokalizacja = _clean(attrs[-1].get_text(" ", strip=True))
            else:
                lokalizacja = _clean(loc.get_text(" ", strip=True))

        # Data licytacji (Poczatek).
        data_licytacji = _clean(_card_text_by_label(card, "Poczatek"))
        if not data_licytacji:
            data_licytacji = _clean(_card_text_by_label(card, "Początek"))

        results.append(
            Auction(
                tytul=tytul,
                kategoria=kategoria,
                cena_wywolawcza=_card_price(card, primary=True),
                wartosc_szacunkowa=_card_price(card, primary=False),
                lokalizacja=lokalizacja,
                data_licytacji=data_licytacji,
                url=url,
            )
        )

    return results


def fetch_listing(
    main_category: str = "MOVABLE",
    province: Optional[str] = None,
    session: Optional[requests.Session] = None,
    timeout: int = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
    backoff: float = DEFAULT_BACKOFF,
    throttle: float = DEFAULT_THROTTLE,
    user_agent: str = DEFAULT_USER_AGENT,
) -> List[Auction]:
    """Pobiera i parsuje listing licytacji z portalu komorniczego.

    main_category: MOVABLE (ruchomosci) lub REAL_ESTATE.
    Zwraca liste Auction. W razie bledu sieci ponawia z backoffem.
    """
    sess = session or requests.Session()
    sess.headers.update({"User-Agent": user_agent, "Accept-Language": "pl-PL,pl"})

    params = {"mainCategory": main_category}
    if province:
        params["province"] = province

    last_exc: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            resp = sess.get(
                BASE_URL + SEARCH_PATH,
                params=params,
                timeout=timeout,
            )
            resp.raise_for_status()
            time.sleep(throttle)
            return parse_listing(resp.text)
        except requests.RequestException as exc:  # pragma: no cover - siec
            last_exc = exc
            if attempt < retries:
                time.sleep(backoff * attempt)
    raise RuntimeError(
        f"Nie udalo sie pobrac listingu po {retries} probach: {last_exc}"
    )


# --- Tryb demo: wbudowany przyklad (offline, bez sieci) -------------------

DEMO_HTML = """
<div class="auction">
  <a href="/licytacje/82116/opel-astra-kombi">
    <div class="auction__tags">
      <span class="cds-chip__content-wrapper">samochody osobowe</span>
    </div>
    <div class="auction__content">
      <h2>samochod osobowy Opel Astra Kombi 1.9CDTI r.pr.2007</h2>
      <div class="auction__row auction__row--location">
        ul. Ksiecia Ziemowita 59, 03-788 Warszawa
      </div>
      <div class="auction__row auction__row--dates">
        Poczatek:\n09.09.2026 10:00
      </div>
      <div class="auction__prices">
        <div class="auction__price auction__price--primary">1500,00 zl</div>
        <div class="auction__price">2000,00 zl</div>
      </div>
    </div>
  </a>
</div>
<div class="auction">
  <a href="/licytacje/83001/koparka-jcb">
    <div class="auction__tags">
      <span class="cds-chip__content-wrapper">maszyny budowlane</span>
    </div>
    <div class="auction__content">
      <h2>Koparko-ladowarka JCB 3CX 2015</h2>
      <div class="auction__row auction__row--location">
        Kielecka 12, 25-001 Kielce
      </div>
      <div class="auction__row auction__row--dates">
        Poczatek:\n20.09.2026 09:00
      </div>
      <div class="auction__prices">
        <div class="auction__price auction__price--primary">78 000,00 zl</div>
        <div class="auction__price">150 000,00 zl</div>
      </div>
    </div>
  </a>
</div>
<div class="auction">
  <a href="/licytacje/83112/ciagnik-ursus">
    <div class="auction__tags">
      <span class="cds-chip__content-wrapper">maszyny rolnicze</span>
    </div>
    <div class="auction__content">
      <h2>Ciagnik rolniczy Ursus C-360 1988</h2>
      <div class="auction__row auction__row--location">
        Polna 3, 20-400 Lublin
      </div>
      <div class="auction__row auction__row--dates">
        Poczatek:\n25.09.2026 11:00
      </div>
      <div class="auction__prices">
        <div class="auction__price auction__price--primary">9 000,00 zl</div>
        <div class="auction__price">12 000,00 zl</div>
      </div>
    </div>
  </a>
</div>
"""


def demo_auctions() -> List[Auction]:
    """Zwraca liste ogloszen z wbudowanego przykladu (bez sieci)."""
    return parse_listing(DEMO_HTML)
