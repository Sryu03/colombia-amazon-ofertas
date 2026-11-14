"""Descubridor gratuito de ASINs en tendencia y ofertas de Amazon.com (0 tokens LLM)."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any
from urllib import request as urllib_request

try:
    from scrapling.fetchers import FetcherSession  # type: ignore
    HAS_SCRAPLING = True
except ImportError:  # pragma: no cover
    FetcherSession = None
    HAS_SCRAPLING = False


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


def _fetch_html(url: str, timeout: int = 12) -> str:
    """Obtiene HTML de una página pública de Amazon usando Scrapling o urllib."""
    if HAS_SCRAPLING and FetcherSession is not None:
        try:
            with FetcherSession(impersonate="chrome", timeout=timeout) as session:
                resp = session.get(url)
                html = getattr(resp, "text", "") or str(getattr(resp, "body", ""))
                if html and "captcha" not in html.lower():
                    return html
        except Exception:
            pass

    try:
        req = urllib_request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "es-US,es;q=0.9,en;q=0.8",
            },
        )
        with urllib_request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                return resp.read().decode("utf-8", errors="ignore")
    except Exception:
        pass
    return ""


def discover_trending_asins(
    existing_asins: set[str] | None = None,
    max_new_asins: int = 40,
    timeout: int = 12,
    delay_seconds: float = 0.8,
) -> list[dict[str, str]]:
    """
    Descubre ASINs reales en tendencia desde Best Sellers / Movers & Shakers.
    Retorna lista de dicts {"asin": ..., "category": ...} sin repetir los existentes.
    """
    known = {a.upper() for a in (existing_asins or set())}
    discovered: list[dict[str, str]] = []

    for category, feed_url in DISCOVERY_FEEDS:
        if len(discovered) >= max_new_asins:
            break
        html = _fetch_html(feed_url, timeout=timeout)
        asins = extract_asins_from_listing_html(html, limit=20)
        for asin in asins:
            if asin not in known:
                known.add(asin)
                discovered.append({"asin": asin, "category": category})
                if len(discovered) >= max_new_asins:
                    break
        if delay_seconds > 0:
            time.sleep(delay_seconds)

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
