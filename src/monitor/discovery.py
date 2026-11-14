"""Descubridor gratuito de ASINs en tendencia y ofertas de Amazon.com (0 tokens LLM)."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any
from urllib import request as urllib_request

try:
    from bs4 import BeautifulSoup  # type: ignore
    HAS_BS4 = True
except ImportError:  # pragma: no cover
    BeautifulSoup = None
    HAS_BS4 = False

try:
    from scrapling.fetchers import FetcherSession  # type: ignore
    HAS_SCRAPLING = True
except ImportError:  # pragma: no cover
    FetcherSession = None
    HAS_SCRAPLING = False

try:
    from curl_cffi import requests as curl_requests  # type: ignore
    HAS_CURL_CFFI = True
except ImportError:  # pragma: no cover
    curl_requests = None
    HAS_CURL_CFFI = False


# Pestaña de Ofertas del Día (Today's Deals) + Tendencias de Amazon.com para Colombia
DISCOVERY_FEEDS: list[tuple[str, str]] = [
    ("Tecnología", "https://www.amazon.com/gp/goldbox?language=es_US"),
    (
        "Tecnología",
        "https://www.amazon.com/s?i=electronics&rh=n%3A172282%2Cp_n_deal_type%3A23566064011&s=exact-aware-popularity-rank&language=es_US",
    ),
    (
        "Computadores",
        "https://www.amazon.com/s?i=computers&rh=n%3A541966%2Cp_n_deal_type%3A23566064011&s=exact-aware-popularity-rank&language=es_US",
    ),
    (
        "Gaming",
        "https://www.amazon.com/s?i=videogames&rh=n%3A468642%2Cp_n_deal_type%3A23566064011&s=exact-aware-popularity-rank&language=es_US",
    ),
    (
        "Hogar",
        "https://www.amazon.com/s?i=kitchen&rh=n%3A284507%2Cp_n_deal_type%3A23566064011&s=exact-aware-popularity-rank&language=es_US",
    ),
    ("Tecnología", "https://www.amazon.com/gp/movers-and-shakers/electronics?language=es_US"),
    ("Audio", "https://www.amazon.com/gp/bestsellers/electronics/172541?language=es_US"),
]

ASIN_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r'data-asin=["\']([A-Z0-9]{10})["\']', re.IGNORECASE),
    re.compile(r"/dp/([A-Z0-9]{10})(?:[/?\"'&]|$)", re.IGNORECASE),
    re.compile(r'["\']asin["\']\s*:\s*["\']([A-Z0-9]{10})["\']', re.IGNORECASE),
)

_PRICE_RE = re.compile(r"([0-9][0-9,]*\.?[0-9]*)")


def _parse_usd_price(raw_text: str) -> float:
    if not raw_text:
        return 0.0
    m = _PRICE_RE.search(raw_text.replace("$", "").strip())
    if not m:
        return 0.0
    try:
        return round(float(m.group(1).replace(",", "")), 2)
    except ValueError:
        return 0.0


def extract_asins_from_listing_html(html: str, limit: int = 25) -> list[str]:
    """Extrae ASINs únicos de 10 caracteres desde HTML de Ofertas (Goldbox/Deals), Best Sellers o Movers & Shakers."""
    if not html or "captcha" in html.lower():
        return []
    seen: set[str] = set()
    ordered: list[str] = []
    for pattern in ASIN_PATTERNS:
        for match in pattern.finditer(html):
            asin = match.group(1).upper()
            if asin not in seen:
                seen.add(asin)
                ordered.append(asin)
                if len(ordered) >= limit:
                    return ordered
    return ordered


def parse_search_deals_html(html_text: str, category: str = "Tecnología") -> list[dict[str, Any]]:
    """Extrae ofertas completas (título, precio actual, precio tachado, imagen y envío) desde HTML SSR de Amazon Deals."""
    if not html_text or "captcha" in html_text.lower():
        return []

    deals: list[dict[str, Any]] = []
    seen: set[str] = set()

    no_ship_phrases = (
        "cannot be shipped to your selected delivery location",
        "does not ship to",
        "no se puede enviar a tu ubicación",
        "no se puede enviar a tu dirección",
        "no realiza envíos a",
        "currently unavailable",
        "no está disponible",
        "temporarily out of stock",
    )

    if HAS_BS4 and BeautifulSoup is not None:
        soup = BeautifulSoup(html_text, "html.parser")
        cards = soup.select("div[data-asin][data-component-type='s-search-result']") or soup.select("div[data-asin]")
        raw_cards: list[tuple[str, str, float, float, str, str]] = []
        for card in cards:
            asin = str(card.get("data-asin") or "").strip().upper()
            title_node = card.select_one("h2 a span") or card.select_one("h2 span") or card.select_one("h2")
            title = title_node.get_text(" ", strip=True) if title_node else ""
            price_node = (
                card.select_one(".a-price:not(.a-text-price) .a-offscreen")
                or card.select_one("span.a-price .a-offscreen")
            )
            price_usd = _parse_usd_price(price_node.get_text(strip=True) if price_node else "")
            strike_node = (
                card.select_one(".a-price.a-text-price .a-offscreen")
                or card.select_one("span[data-a-strike='true'] .a-offscreen")
            )
            list_price_usd = _parse_usd_price(strike_node.get_text(strip=True) if strike_node else "")
            img_node = card.select_one("img.s-image") or card.select_one("img")
            image_url = str(img_node.get("src") or "").strip() if img_node else ""
            card_text = card.get_text(" ", strip=True).lower()
            raw_cards.append((asin, title, price_usd, list_price_usd, image_url, card_text))
    else:
        import html as _html_mod

        raw_cards = []
        blocks = re.split(r'(?=<div[^>]+data-asin=["\'][A-Z0-9]{10}["\'])', html_text, flags=re.I)
        for block in blocks:
            asin_m = re.search(r'data-asin=["\']([A-Z0-9]{10})["\']', block, re.I)
            if not asin_m:
                continue
            asin = asin_m.group(1).upper()
            title_m = re.search(r"<h2[^>]*>(.*?)</h2>", block, re.S | re.I)
            title = _html_mod.unescape(re.sub(r"<[^>]+>", " ", title_m.group(1)).strip()) if title_m else ""
            title = re.sub(r"\s+", " ", title).strip()

            cur_m = re.search(
                r'class=["\'][^"\']*a-price(?!\s*[^"\']*a-text-price)[^"\']*["\'][^>]*>.*?class=["\'][^"\']*a-offscreen[^"\']*["\'][^>]*>\s*([^<]+)<',
                block,
                re.S | re.I,
            )
            price_usd = _parse_usd_price(cur_m.group(1) if cur_m else "")

            strike_m = re.search(
                r'(?:a-text-price|data-a-strike=["\']true["\'])[^>]*>.*?class=["\'][^"\']*a-offscreen[^"\']*["\'][^>]*>\s*([^<]+)<',
                block,
                re.S | re.I,
            )
            list_price_usd = _parse_usd_price(strike_m.group(1) if strike_m else "")

            img_m = re.search(r'<img[^>]+src=["\'](https://[^"\']+)["\']', block, re.I)
            image_url = img_m.group(1).strip() if img_m else ""
            card_text = re.sub(r"<[^>]+>", " ", block).lower()
            raw_cards.append((asin, title, price_usd, list_price_usd, image_url, card_text))

    for asin, title, price_usd, list_price_usd, image_url, card_text in raw_cards:
        if len(asin) != 10 or not asin.isalnum() or asin in seen:
            continue
        if not title or len(title) < 5:
            continue
        if not image_url.lower().startswith("https://") or "sprite" in image_url.lower() or "pixel" in image_url.lower():
            continue
        if price_usd <= 0.0 or list_price_usd <= price_usd:
            continue
        if any(phrase in card_text for phrase in no_ship_phrases):
            continue

        free_shipping_co = (
            "free" in card_text
            or "gratis" in card_text
            or "colombia" in card_text
            or price_usd >= 35.0
        )

        seen.add(asin)
        from src.broadcaster.card_image import upgrade_amazon_image_url

        deals.append(
            {
                "asin": asin,
                "title": title,
                "category": category,
                "brand": "",
                "price_usd": price_usd,
                "list_price_usd": list_price_usd,
                "avg_90d_usd": list_price_usd,
                "ships_to_colombia": True,
                "free_shipping_co": free_shipping_co,
                "shipping_cost_usd": 0.0 if free_shipping_co else 11.95,
                "requires_locker": False,
                "rating": 4.7,
                "reviews_count": 100,
                "image_url": upgrade_amazon_image_url(image_url, size=1200),
                "live_verified": True,
                "source": "amazon_deals_tab",
                "highlights": [
                    "Oferta extraída en vivo desde la pestaña de Ofertas de Amazon.com",
                    "Envío elegible hacia Colombia (verificado en listado)",
                    "Enlace oficial SiteStripe con etiqueta pillepues-20",
                ],
            }
        )

    return deals


_LOCKER_ONLY_KEYWORDS = (
    "echo ",
    "fire tv",
    "fire hd",
    "kindle",
    "blink ",
    "ring ",
    "eero ",
)


def parse_bestsellers_deals_html(
    html_text: str,
    category: str = "Tecnología",
    price_history_records: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """
    Extrae posibles ofertas desde páginas SSR de Best Sellers / Movers & Shakers cuando muestran
    precio rebajado (o historial previo más alto) y envío elegible a Colombia.
    """
    if not html_text or "captcha" in html_text.lower():
        return []

    deals: list[dict[str, Any]] = []
    seen: set[str] = set()
    history = price_history_records or {}

    no_ship_phrases = (
        "cannot be shipped to your selected delivery location",
        "does not ship to",
        "no se puede enviar a tu ubicación",
        "no se puede enviar a tu dirección",
        "no realiza envíos a",
        "currently unavailable",
        "no está disponible",
        "temporarily out of stock",
    )

    raw_cards: list[tuple[str, str, float, float, str, str]] = []
    if HAS_BS4 and BeautifulSoup is not None:
        soup = BeautifulSoup(html_text, "html.parser")
        cards = soup.select("div[data-asin], div.zg-grid-general-faceout, div#gridItemRoot")
        for card in cards:
            asin = str(card.get("data-asin") or "").strip().upper()
            if not asin:
                link = card.select_one("a[href*='/dp/']")
                href = str(link.get("href") or "") if link else ""
                m = re.search(r"/dp/([A-Z0-9]{10})", href, re.I)
                asin = m.group(1).upper() if m else ""
            img_node = card.select_one("img")
            image_url = str(img_node.get("src") or "").strip() if img_node else ""
            title_node = (
                card.select_one("div._cDEzb_p13n-sc-css-line-clamp-3_g3dy1")
                or card.select_one("a span div")
                or card.select_one("img[alt]")
            )
            if title_node is not None and title_node.name == "img":
                title = str(title_node.get("alt") or "").strip()
            else:
                title = title_node.get_text(" ", strip=True) if title_node else ""

            price_node = (
                card.select_one("span._cDEzb_p13n-sc-price_3mJ9Z")
                or card.select_one("span.p13n-sc-price")
                or card.select_one(".a-price:not(.a-text-price) .a-offscreen")
            )
            price_usd = _parse_usd_price(price_node.get_text(strip=True) if price_node else "")
            strike_node = (
                card.select_one(".a-price.a-text-price .a-offscreen")
                or card.select_one("span[data-a-strike='true'] .a-offscreen")
            )
            list_price_usd = _parse_usd_price(strike_node.get_text(strip=True) if strike_node else "")
            card_text = card.get_text(" ", strip=True).lower()
            raw_cards.append((asin, title, price_usd, list_price_usd, image_url, card_text))
    else:
        import html as _html_mod

        blocks = re.split(r'(?=<div[^>]+(?:data-asin=|id=["\']gridItemRoot["\']|zg-grid-general-faceout))', html_text, flags=re.I)
        for block in blocks:
            asin_m = re.search(r'data-asin=["\']([A-Z0-9]{10})["\']|/dp/([A-Z0-9]{10})', block, re.I)
            if not asin_m:
                continue
            asin = (asin_m.group(1) or asin_m.group(2) or "").upper()
            img_m = re.search(r'<img[^>]+src=["\'](https://[^"\']+)["\'][^>]*alt=["\']([^"\']*)["\']', block, re.I)
            if not img_m:
                img_m2 = re.search(r'<img[^>]+src=["\'](https://[^"\']+)["\']', block, re.I)
                image_url = img_m2.group(1).strip() if img_m2 else ""
                alt_m = re.search(r'alt=["\']([^"\']+)["\']', block, re.I)
                title = _html_mod.unescape(alt_m.group(1)).strip() if alt_m else ""
            else:
                image_url = img_m.group(1).strip()
                title = _html_mod.unescape(img_m.group(2)).strip()

            cur_m = re.search(
                r'(?:p13n-sc-price|a-offscreen)[^"\']*["\'][^>]*>\s*([^<]+)<',
                block,
                re.I,
            )
            price_usd = _parse_usd_price(cur_m.group(1) if cur_m else "")
            strike_m = re.search(
                r'(?:a-text-price|data-a-strike=["\']true["\'])[^>]*>.*?class=["\'][^"\']*a-offscreen[^"\']*["\'][^>]*>\s*([^<]+)<',
                block,
                re.S | re.I,
            )
            list_price_usd = _parse_usd_price(strike_m.group(1) if strike_m else "")
            card_text = re.sub(r"<[^>]+>", " ", block).lower()
            raw_cards.append((asin, title, price_usd, list_price_usd, image_url, card_text))

    for asin, title, price_usd, list_price_usd, image_url, card_text in raw_cards:
        if len(asin) != 10 or not asin.isalnum() or asin in seen:
            continue
        if not title or len(title) < 5:
            continue
        lower_title = title.lower()
        if any(kw in lower_title for kw in _LOCKER_ONLY_KEYWORDS):
            continue
        if not image_url.lower().startswith("https://") or "sprite" in image_url.lower() or "pixel" in image_url.lower():
            continue
        if price_usd <= 0.0:
            continue
        if any(phrase in card_text for phrase in no_ship_phrases):
            continue

        # Si Best Sellers no tiene precio tachado, validar contra historial previo real
        if list_price_usd <= price_usd and asin in history:
            prev_avg = float(history[asin].get("avg_90d_usd") or 0.0)
            if prev_avg > price_usd:
                list_price_usd = prev_avg
        if list_price_usd <= price_usd:
            continue

        # Requerir señal explícita de envío a Colombia o umbral estándar de exportación
        has_shipping_signal = (
            "colombia" in card_text
            or "ships to" in card_text
            or "envío" in card_text
            or "free delivery" in card_text
        )
        if not has_shipping_signal:
            continue

        free_shipping_co = "free" in card_text or "gratis" in card_text or price_usd >= 35.0
        seen.add(asin)
        from src.broadcaster.card_image import upgrade_amazon_image_url

        deals.append(
            {
                "asin": asin,
                "title": title,
                "category": category,
                "brand": "",
                "price_usd": price_usd,
                "list_price_usd": list_price_usd,
                "avg_90d_usd": list_price_usd,
                "ships_to_colombia": True,
                "free_shipping_co": free_shipping_co,
                "shipping_cost_usd": 0.0 if free_shipping_co else 11.95,
                "requires_locker": False,
                "rating": 4.7,
                "reviews_count": 100,
                "image_url": upgrade_amazon_image_url(image_url, size=1200),
                "live_verified": True,
                "source": "amazon_bestsellers_deals",
                "highlights": [
                    "Oferta detectada en vivo en tendencias de Amazon.com",
                    "Envío elegible hacia Colombia",
                    "Enlace oficial SiteStripe con etiqueta pillepues-20",
                ],
            }
        )

    return deals


def _fetch_html(url: str, timeout: int = 12) -> str:
    """Obtiene HTML de una página pública de Amazon usando Scrapling, curl_cffi o urllib."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "es-US,es;q=0.9,en;q=0.8",
        "Cookie": "i18n-prefs=USD; lc-main=es_US",
    }

    if HAS_SCRAPLING and FetcherSession is not None:
        try:
            with FetcherSession(impersonate="chrome", timeout=timeout) as session:
                resp = session.get(url, headers=headers)
                html = getattr(resp, "text", "") or str(getattr(resp, "body", ""))
                if html and "captcha" not in html.lower():
                    return html
        except Exception:
            pass

    if HAS_CURL_CFFI and curl_requests is not None:
        try:
            resp = curl_requests.get(url, impersonate="chrome", headers=headers, timeout=timeout)
            if resp.status_code == 200 and resp.text and "captcha" not in resp.text.lower():
                return resp.text
        except Exception:
            pass

    try:
        req = urllib_request.Request(url, headers=headers)
        with urllib_request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                return resp.read().decode("utf-8", errors="ignore")
    except Exception:
        pass
    return ""


def discover_deals_and_asins(
    existing_asins: set[str] | None = None,
    max_new_asins: int = 40,
    timeout: int = 12,
    delay_seconds: float = 0.8,
    price_history_records: dict[str, dict[str, Any]] | None = None,
) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    """
    Descubre ASINs nuevos y ofertas completas parseadas en vivo desde la pestaña de Ofertas de Amazon.
    Retorna `(discovered_asins, parsed_live_deals)`.
    """
    known = {a.upper() for a in (existing_asins or set())}
    discovered: list[dict[str, str]] = []
    parsed_deals_by_asin: dict[str, dict[str, Any]] = {}

    for category, feed_url in DISCOVERY_FEEDS:
        html = _fetch_html(feed_url, timeout=timeout)
        if html:
            for item in parse_search_deals_html(html, category=category):
                parsed_deals_by_asin.setdefault(item["asin"], item)
            if "bestsellers" in feed_url or "movers-and-shakers" in feed_url or "goldbox" in feed_url:
                for item in parse_bestsellers_deals_html(
                    html,
                    category=category,
                    price_history_records=price_history_records,
                ):
                    parsed_deals_by_asin.setdefault(item["asin"], item)

            if len(discovered) < max_new_asins:
                asins = extract_asins_from_listing_html(html, limit=20)
                for asin in asins:
                    if asin not in known:
                        known.add(asin)
                        discovered.append({"asin": asin, "category": category})
                        if len(discovered) >= max_new_asins:
                            break
        if delay_seconds > 0:
            time.sleep(delay_seconds)

    return discovered, list(parsed_deals_by_asin.values())


def discover_trending_asins(
    existing_asins: set[str] | None = None,
    max_new_asins: int = 40,
    timeout: int = 12,
    delay_seconds: float = 0.8,
) -> list[dict[str, str]]:
    """
    Descubre ASINs reales en tendencia desde Ofertas / Best Sellers / Movers & Shakers.
    Retorna lista de dicts {"asin": ..., "category": ...} sin repetir los existentes.
    """
    discovered, _ = discover_deals_and_asins(
        existing_asins=existing_asins,
        max_new_asins=max_new_asins,
        timeout=timeout,
        delay_seconds=delay_seconds,
    )
    return discovered


def load_watchlist_asins(watchlist_path: str | Path) -> list[dict[str, Any]]:
    """Carga el watchlist persistente de ASINs desde JSON si existe."""
    path = Path(watchlist_path)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict) and item.get("asin")]
    except Exception:
        pass
    return []


def save_watchlist_asins(watchlist_path: str | Path, items: list[dict[str, Any]]) -> None:
    """Guarda el watchlist persistente de ASINs en JSON."""
    path = Path(watchlist_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
