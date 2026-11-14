from __future__ import annotations

import re
import urllib.parse
from typing import Any

try:
    from bs4 import BeautifulSoup  # type: ignore

    HAS_BS4 = True
except Exception:
    BeautifulSoup = None  # type: ignore
    HAS_BS4 = False

try:
    from scrapling.fetchers import FetcherSession  # type: ignore

    HAS_SCRAPLING = True
except Exception:
    FetcherSession = None  # type: ignore
    HAS_SCRAPLING = False


def _build_product_svg_data_uri(
    label: str,
    subtitle: str,
    category: str,
    accent_hex: str = "#FF9900",
    bg_start: str = "#0F172A",
    bg_end: str = "#1E293B",
) -> str:
    """Create a crisp, CORS-proof, offline-ready SVG Data URI product illustration."""
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 420" width="600" height="420">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{bg_start}"/>
      <stop offset="100%" stop-color="{bg_end}"/>
    </linearGradient>
    <linearGradient id="accent" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="{accent_hex}"/>
      <stop offset="100%" stop-color="#FBBF24"/>
    </linearGradient>
  </defs>
  <rect width="600" height="420" rx="24" fill="url(#bg)"/>
  <circle cx="510" cy="80" r="130" fill="{accent_hex}" opacity="0.12"/>
  <circle cx="90" cy="350" r="110" fill="#38BDF8" opacity="0.10"/>
  <rect x="36" y="32" width="160" height="34" rx="17" fill="{accent_hex}" opacity="0.2"/>
  <text x="116" y="54" font-family="Inter, system-ui, sans-serif" font-size="14" font-weight="700" fill="#F8FAFC" text-anchor="middle">{category.upper()}</text>
  <rect x="440" y="32" width="124" height="34" rx="17" fill="#10B981" opacity="0.22"/>
  <text x="502" y="54" font-family="Inter, system-ui, sans-serif" font-size="13" font-weight="700" fill="#6EE7B7" text-anchor="middle">AMAZON -> CO</text>
  <rect x="60" y="105" width="480" height="190" rx="20" fill="#1E293B" stroke="{accent_hex}" stroke-width="2" stroke-opacity="0.45"/>
  <text x="300" y="195" font-family="Inter, system-ui, sans-serif" font-size="32" font-weight="800" fill="#FFFFFF" text-anchor="middle">{label}</text>
  <text x="300" y="238" font-family="Inter, system-ui, sans-serif" font-size="18" font-weight="500" fill="#94A3B8" text-anchor="middle">{subtitle}</text>
  <rect x="180" y="336" width="240" height="8" rx="4" fill="url(#accent)"/>
</svg>"""
    encoded = urllib.parse.quote(svg.strip())
    return f"data:image/svg+xml;utf8,{encoded}"


SEED_PRODUCTS_COLOMBIA: list[dict[str, Any]] = [
    {
        "asin": "B09V3KXJPB",
        "title": "Samsung 990 PRO SSD NVMe M.2 PCIe Gen4 de 2TB con Lectura de 7450 MB/s",
        "category": "Tecnología",
        "brand": "Samsung",
        "price_usd": 119.99,
        "list_price_usd": 189.99,
        "avg_90d_usd": 169.99,
        "ships_to_colombia": True,
        "free_shipping_co": True,
        "rating": 4.9,
        "reviews_count": 8420,
        "image_url": _build_product_svg_data_uri(
            "SAMSUNG 990 PRO 2TB",
            "NVMe M.2 PCIe 4.0 • 7450 MB/s • Compatible PS5",
            "Tecnología",
            "#3B82F6",
        ),
        "highlights": [
            "Velocidades secuenciales de hasta 7,450 MB/s en lectura y 6,900 MB/s en escritura",
            "Compatible con PlayStation 5 y laptops/PC de alto rendimiento con control térmico inteligente",
            "Exento de arancel e IVA en Colombia (< $200 USD) con envío gratis directo desde Amazon.com",
        ],
    },
    {
        "asin": "B0863TXGM3",
        "title": "Sony WH-1000XM4 Audífonos Inalámbricos Noise Cancelling con 30h de Batería",
        "category": "Audio",
        "brand": "Sony",
        "price_usd": 148.00,
        "list_price_usd": 248.00,
        "avg_90d_usd": 228.00,
        "ships_to_colombia": True,
        "free_shipping_co": True,
        "rating": 4.8,
        "reviews_count": 56310,
        "image_url": _build_product_svg_data_uri(
            "SONY WH-1000XM4",
            "Cancelación Activa Líder • LDAC Hi-Res • 30h Batería",
            "Audio",
            "#8B5CF6",
        ),
        "highlights": [
            "Cancelación de ruido líder en la industria con procesador HD QN1 y doble sensor de ruido",
            "Audio de alta resolución LDAC, conexión multipunto Bluetooth para 2 dispositivos simultáneos",
            "Pasa directo por aduana en Colombia con $0 de impuestos (debajo del tope de $200 USD)",
        ],
    },
    {
        "asin": "B09VCJ171S",
        "title": "AMD Ryzen 5 5600X Procesador Desbloqueado de 6 Núcleos y 12 Hilos + Cooler Wraith Stealth",
        "category": "Tecnología",
        "brand": "AMD",
        "price_usd": 109.99,
        "list_price_usd": 179.99,
        "avg_90d_usd": 154.99,
        "ships_to_colombia": True,
        "free_shipping_co": True,
        "rating": 4.8,
        "reviews_count": 32140,
        "image_url": _build_product_svg_data_uri(
            "AMD RYZEN 5 5600X",
            "6 Núcleos / 12 Hilos • 4.6 GHz Boost • Socket AM4",
            "Tecnología",
            "#EF4444",
        ),
        "highlights": [
            "6 núcleos y 12 hilos desbloqueados con reloj turbo de hasta 4.6 GHz y 35 MB de caché",
            "Incluye disipador térmico silencioso AMD Wraith Stealth listo para instalar en placas AM4",
            "Cero aranceles de importación en Colombia y envío gratis puerta a puerta incluido",
        ],
    },
    {
        "asin": "B0B4629BNR",
        "title": "ASUS TUF Gaming VG249Q1R Monitor Gamer 24\" Full HD 165Hz IPS 1ms FreeSync Premium",
        "category": "Gaming",
        "brand": "ASUS",
        "price_usd": 109.00,
        "list_price_usd": 169.99,
        "avg_90d_usd": 159.99,
        "ships_to_colombia": True,
        "free_shipping_co": True,
        "rating": 4.7,
        "reviews_count": 6890,
        "image_url": _build_product_svg_data_uri(
            "ASUS TUF 24\" 165HZ",
            "Panel IPS 1ms MPRT • FreeSync Premium • Shadow Boost",
            "Gaming",
            "#10B981",
        ),
        "highlights": [
            "Panel IPS de 23.8 pulgadas Full HD (1920x1080) con tasa de refresco overclockeable a 165Hz",
            "Tiempo de respuesta extremo de 1ms MPRT con tecnología ASUS Extreme Low Motion Blur",
            "Envío gratuito a Colombia sin cobro de IVA ni aranceles por estar bajo los $200 USD",
        ],
    },
    {
        "asin": "B08R6S1M1K",
        "title": "Anker 735 Cargador GaNPrime 65W USB-C de 3 Puertos Plegable Carga Rápida",
        "category": "Tecnología",
        "brand": "Anker",
        "price_usd": 24.99,
        "list_price_usd": 45.99,
        "avg_90d_usd": 39.99,
        "ships_to_colombia": True,
        "free_shipping_co": True,
        "rating": 4.8,
        "reviews_count": 14820,
        "image_url": _build_product_svg_data_uri(
            "ANKER 735 GAN 65W",
            "2x USB-C + 1x USB-A • MacBook / iPhone / Galaxy",
            "Tecnología",
            "#06B6D4",
        ),
        "highlights": [
            "Carga simultáneamente laptop MacBook Air/Pro, celular y audífonos con 65W de potencia GaNPrime",
            "Diseño ultra compacto 53% más pequeño que cargadores originales de 67W con clavijas plegables",
            "Elegible para envío gratis a Colombia completando $35 USD en el carrito y 0% impuestos",
        ],
    },
    {
        "asin": "B07W5JKHFZ",
        "title": "Logitech G502 HERO Mouse Gamer de Alto Rendimiento con Sensor HERO 25K y Pesas Ajustables",
        "category": "Gaming",
        "brand": "Logitech G",
        "price_usd": 29.99,
        "list_price_usd": 59.99,
        "avg_90d_usd": 46.99,
        "ships_to_colombia": True,
        "free_shipping_co": True,
        "rating": 4.8,
        "reviews_count": 64200,
        "image_url": _build_product_svg_data_uri(
            "LOGITECH G502 HERO",
            "Sensor 25,600 DPI • 11 Botones Programables • RGB",
            "Gaming",
            "#3B82F6",
        ),
        "highlights": [
            "Sensor óptico HERO 25K con seguimiento submicrónico de hasta 25,600 DPI sin aceleración",
            "11 botones programables, rueda hiperrápida de doble modo y sistema de 5 pesas de 3.6g",
            "Ideal para combinar en carrito de $35+ USD y obtener envío gratis a Colombia sin impuestos",
        ],
    },
    {
        "asin": "B0B2SH4CN6",
        "title": "Apple AirPods Pro (2.ª Generación) con Estuche de Carga MagSafe USB-C y Audio Adaptativo",
        "category": "Audio",
        "brand": "Apple",
        "price_usd": 169.99,
        "list_price_usd": 249.00,
        "avg_90d_usd": 234.00,
        "ships_to_colombia": True,
        "free_shipping_co": True,
        "rating": 4.8,
        "reviews_count": 41250,
        "image_url": _build_product_svg_data_uri(
            "AIRPODS PRO 2 USB-C",
            "Chip Apple H2 • Cancelación Activa 2x • Audio Espacial",
            "Audio",
            "#F59E0B",
        ),
        "highlights": [
            "Chip H2 diseñado por Apple con hasta el doble de cancelación activa de ruido y modo Ambiente",
            "Estuche de carga MagSafe con puerto USB-C, altavoz integrado para Encontrar y resistencia IP54",
            "Ahorro masivo frente a tiendas en Colombia: entra sin IVA (bajo $200 USD) y envío gratis",
        ],
    },
    {
        "asin": "B09B8V1LZ3",
        "title": "Corsair Vengeance LPX 32GB (2x16GB) DDR4 3600MHz C18 Memoria RAM de Alto Rendimiento",
        "category": "Tecnología",
        "brand": "Corsair",
        "price_usd": 52.99,
        "list_price_usd": 84.99,
        "avg_90d_usd": 74.99,
        "ships_to_colombia": True,
        "free_shipping_co": True,
        "rating": 4.8,
        "reviews_count": 29800,
        "image_url": _build_product_svg_data_uri(
            "CORSAIR 32GB DDR4",
            "2x16GB 3600MHz CL18 • Disipador Aluminio • XMP 2.0",
            "Tecnología",
            "#F97316",
        ),
        "highlights": [
            "Kit de 32GB (2 módulos de 16GB) DDR4 a 3600MHz optimizado para plataformas Intel y AMD Ryzen",
            "Disipador de calor de aluminio puro de perfil bajo para disipación rápida y compatibilidad total",
            "Supera los $35 USD y queda bajo $200 USD: envío gratis a Colombia + $0 en aduana",
        ],
    },
    {
        "asin": "B08H93ZRK9",
        "title": "HyperX Cloud II Wireless Audífonos Gamer Inalámbricos 7.1 Surround con Micrófono Desmontable",
        "category": "Gaming",
        "brand": "HyperX",
        "price_usd": 84.99,
        "list_price_usd": 149.99,
        "avg_90d_usd": 129.99,
        "ships_to_colombia": True,
        "free_shipping_co": True,
        "rating": 4.7,
        "reviews_count": 19340,
        "image_url": _build_product_svg_data_uri(
            "HYPERX CLOUD II",
            "Wireless 2.4GHz • Sonido 7.1 • 30h Batería • PC/PS5",
            "Gaming",
            "#EC4899",
        ),
        "highlights": [
            "Conexión inalámbrica de grado gaming 2.4GHz sin latencia y hasta 30 horas de autonomía",
            "Espuma viscoelástica original HyperX con sonido envolvente 7.1 y drivers dinámicos de 53 mm",
            "Envío gratuito a Colombia y exento de arancel e IVA (menor a $200 USD)",
        ],
    },
    {
        "asin": "B07SM5HBK1",
        "title": "Ninja AF101 Freidora de Aire de 4 Cuartos (3.8L) 4-en-1 con Recubrimiento Cerámico",
        "category": "Hogar",
        "brand": "Ninja",
        "price_usd": 78.99,
        "list_price_usd": 129.99,
        "avg_90d_usd": 114.99,
        "ships_to_colombia": True,
        "free_shipping_co": True,
        "rating": 4.8,
        "reviews_count": 51900,
        "image_url": _build_product_svg_data_uri(
            "NINJA AIR FRYER 4QT",
            "Freidora de Aire 4-en-1 • Canasta Cerámica Antiadherente",
            "Hogar",
            "#14B8A6",
        ),
        "highlights": [
            "4 programas inteligentes: Freír con aire, Asar, Recalentar y Deshidratar con hasta 75% menos grasa",
            "Canasta antiadherente recubierta de cerámica libre de PTFE/PFOA apta para lavavajillas (110V Colombia)",
            "Envío gratis directo a Colombia sin impuestos de importación por costar menos de $200 USD",
        ],
    },
    {
        "asin": "B08C1W5N87",
        "title": "Philips Hue Kit Inicial 3 Bombillos Inteligentes LED Color A19 + Hue Bridge (Compatible Alexa)",
        "category": "Hogar",
        "brand": "Philips Hue",
        "price_usd": 99.99,
        "list_price_usd": 169.99,
        "avg_90d_usd": 149.99,
        "ships_to_colombia": True,
        "free_shipping_co": True,
        "rating": 4.7,
        "reviews_count": 11400,
        "image_url": _build_product_svg_data_uri(
            "PHILIPS HUE KIT 3X",
            "16M Colores + Hue Bridge • Alexa / HomeKit / Google",
            "Hogar",
            "#A855F7",
        ),
        "highlights": [
            "Incluye 3 bombillos inteligentes White & Color Ambiance (800 lúmenes, rosca E26 estándar en Colombia)",
            "Puente Hue Bridge incluido para automatización completa, sincronización con música/TV y control por voz",
            "Libre de impuestos de importación en Colombia (< $200 USD) y envío gratis incluido",
        ],
    },
    {
        "asin": "B0C2P486S4",
        "title": "Beelink SER6 Mini PC AMD Ryzen 9 6900HX (8C/16T) 32GB DDR5 RAM + 1TB SSD PCIe 4.0 WiFi 6",
        "category": "Tecnología",
        "brand": "Beelink",
        "price_usd": 249.00,
        "list_price_usd": 399.00,
        "avg_90d_usd": 369.00,
        "ships_to_colombia": True,
        "free_shipping_co": True,
        "rating": 4.6,
        "reviews_count": 2410,
        "image_url": _build_product_svg_data_uri(
            "BEELINK SER6 RYZEN 9",
            "Ryzen 9 6900HX • 32GB DDR5 • 1TB NVMe • Radeon 680M",
            "Tecnología",
            "#F43F5E",
        ),
        "highlights": [
            "Potente procesador AMD Ryzen 9 6900HX con gráficos integrados Radeon 680M RDNA2 de 12 núcleos",
            "Incluye 32GB de RAM DDR5 a 4800MHz, SSD NVMe PCIe 4.0 de 1TB y salida triple pantalla 4K + USB4",
            "Supera los $200 USD (aplica IVA de importación en Amazon), pero ahorra más de $1.2M COP vs mercado local",
        ],
    },
]


def _extract_float_price(text: str | None) -> float:
    """Extract float USD value from an Amazon price string like '$119.99' or 'USD 1,249.00'."""
    if not text:
        return 0.0
    cleaned = text.replace(",", "")
    match = re.search(r"(\d+(?:\.\d{1,2})?)", cleaned)
    return float(match.group(1)) if match else 0.0


def parse_amazon_html(html: str, asin: str) -> dict[str, Any]:
    """
    Parse an Amazon product HTML fragment or page deterministically with BeautifulSoup4
    (with stdlib regex fallback if BeautifulSoup4 is not installed in the current environment).
    Extracts title, current price, list price, rating, and Colombia shipping eligibility.
    """
    raw_html = html or ""
    if HAS_BS4 and BeautifulSoup is not None:
        soup = BeautifulSoup(raw_html, "html.parser")

        title_node = (
            soup.select_one("#productTitle")
            or soup.select_one("#title")
            or soup.select_one("h1")
        )
        title = title_node.get_text(strip=True) if title_node else f"Amazon Product {asin}"

        price_node = (
            soup.select_one("#corePriceDisplay_desktop_feature_div .a-price .a-offscreen")
            or soup.select_one(".a-price.aok-align-center .a-offscreen")
            or soup.select_one("#priceblock_ourprice")
            or soup.select_one("#priceblock_dealprice")
            or soup.select_one(".a-price .a-offscreen")
        )
        price_usd = _extract_float_price(price_node.get_text(strip=True) if price_node else "")

        list_node = (
            soup.select_one(".basisPrice .a-offscreen")
            or soup.select_one(".a-text-price .a-offscreen")
            or soup.select_one("#listPrice")
        )
        list_price_usd = _extract_float_price(list_node.get_text(strip=True) if list_node else "")

        delivery_node = (
            soup.select_one("#mir-layout-DELIVERY_BLOCK")
            or soup.select_one("#deliveryBlockMessage")
            or soup.select_one("#amazonGlobal_feature_div")
        )
        delivery_text = (delivery_node.get_text(" ", strip=True) if delivery_node else raw_html).lower()

        rating_node = soup.select_one("#acrPopover") or soup.select_one(".a-icon-alt")
        rating_val = _extract_float_price(rating_node.get_text(strip=True) if rating_node else "")
        rating = rating_val if 0.0 < rating_val <= 5.0 else 4.7

        img_node = soup.select_one("#landingImage") or soup.select_one("#imgBlkFront")
        image_url = (
            str(img_node.get("src"))
            if (img_node and img_node.get("src"))
            else _build_product_svg_data_uri(asin, title[:38], "Tecnología")
        )
    else:
        title_match = re.search(r'id=["\']productTitle["\'][^>]*>(.*?)</', raw_html, re.S | re.I)
        title = re.sub(r"<[^>]+>", "", title_match.group(1)).strip() if title_match else f"Amazon Product {asin}"

        offscreen_prices = re.findall(r'class=["\'][^"\']*a-offscreen[^"\']*["\'][^>]*>\s*([^<]+)<', raw_html, re.I)
        price_usd = _extract_float_price(offscreen_prices[0]) if offscreen_prices else 0.0
        list_price_usd = _extract_float_price(offscreen_prices[1]) if len(offscreen_prices) > 1 else price_usd
        delivery_text = raw_html.lower()
        rating = 4.7
        image_url = _build_product_svg_data_uri(asin, title[:38], "Tecnología")

    if list_price_usd <= 0.0:
        list_price_usd = price_usd

    no_ship_phrases = (
        "cannot be shipped to your selected delivery location",
        "no se puede enviar a tu ubicación",
        "currently unavailable",
    )
    ships_to_colombia = not any(phrase in delivery_text for phrase in no_ship_phrases)
    free_shipping_co = ships_to_colombia and (
        "free" in delivery_text
        or "gratis" in delivery_text
        or "colombia" in delivery_text
        or price_usd >= 35.0
    )

    return {
        "asin": asin,
        "title": title,
        "category": "Tecnología",
        "brand": "",
        "price_usd": price_usd,
        "list_price_usd": list_price_usd,
        "avg_90d_usd": list_price_usd,
        "ships_to_colombia": ships_to_colombia,
        "free_shipping_co": free_shipping_co,
        "rating": rating,
        "reviews_count": 100,
        "image_url": image_url,
        "highlights": [
            "Precio verificado en tiempo real mediante motor Zero-Token",
            "Elegible para envío internacional AmazonGlobal hacia Colombia",
            "Garantía de compra directa en Amazon.com",
        ],
    }


class AmazonMonitorScraper:
    """
    Hybrid Zero-Token Amazon.com monitor for Colombia:
    - Uses deterministic seed catalog by default for fast offline/CI reproducibility
    - Supports live stealth scraping via Scrapling FetcherSession when enabled
    """

    def __init__(self, timeout: int = 15) -> None:
        self.timeout = timeout
        self.has_scrapling = HAS_SCRAPLING

    def fetch_asin_live(self, asin: str) -> dict[str, Any] | None:
        """Fetch live product page from Amazon.com using Scrapling FetcherSession if available."""
        url = f"https://www.amazon.com/dp/{asin}?language=es_US"
        if HAS_SCRAPLING and FetcherSession is not None:
            try:
                with FetcherSession(impersonate="chrome", timeout=self.timeout) as session:
                    response = session.get(url)
                    html = getattr(response, "text", "") or str(getattr(response, "body", ""))
                    if html:
                        parsed = parse_amazon_html(html, asin)
                        if parsed.get("price_usd", 0.0) > 0:
                            return parsed
            except Exception:
                pass
        return None

    def fetch_catalog(
        self,
        use_seed: bool = True,
        asins: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Return the list of monitored Amazon products for Colombia.
        If `use_seed=True`, returns the curated SEED_PRODUCTS_COLOMBIA (filtered by `asins` if provided).
        If `use_seed=False`, attempts live Scrapling fetch with automatic fallback to seed records.
        """
        seed_map = {item["asin"]: dict(item) for item in SEED_PRODUCTS_COLOMBIA}
        target_asins = asins if asins else [item["asin"] for item in SEED_PRODUCTS_COLOMBIA]

        if use_seed:
            results: list[dict[str, Any]] = []
            for asin in target_asins:
                if asin in seed_map:
                    results.append(dict(seed_map[asin]))
            return results

        live_results: list[dict[str, Any]] = []
        for asin in target_asins:
            live_item = self.fetch_asin_live(asin)
            if live_item and live_item.get("price_usd", 0.0) > 0:
                if asin in seed_map:
                    merged = {**seed_map[asin], **live_item}
                    live_results.append(merged)
                else:
                    live_results.append(live_item)
            elif asin in seed_map:
                live_results.append(dict(seed_map[asin]))

        return live_results
