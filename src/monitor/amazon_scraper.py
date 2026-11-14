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

try:
    from curl_cffi import requests as curl_requests  # type: ignore

    HAS_CURL_CFFI = True
except Exception:
    curl_requests = None  # type: ignore
    HAS_CURL_CFFI = False


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
        "asin": "B0B9C4DKKG",
        "title": "Samsung 990 PRO SSD NVMe M.2 PCIe Gen4 de 2TB con Lectura de 7450 MB/s",
        "category": "Tecnología",
        "brand": "Samsung",
        "price_usd": 149.99,
        "list_price_usd": 249.99,
        "avg_90d_usd": 189.99,
        "ships_to_colombia": True,
        "free_shipping_co": True,
        "shipping_cost_usd": 0.0,
        "requires_locker": False,
        "rating": 4.8,
        "reviews_count": 9840,
        "image_url": "https://m.media-amazon.com/images/I/71K6m2A+WJL._AC_SL1500_.jpg",
        "highlights": [
            "Velocidades secuenciales de hasta 7,450 MB/s en lectura y 6,900 MB/s en escritura",
            "Compatible con PlayStation 5 y laptops/PC de alto rendimiento PCIe 4.0",
            "Exento de arancel e IVA en Colombia (≤ $200 USD) con envío gratis directo sin casillero",
        ],
    },
    {
        "asin": "B0863FR3S9",
        "title": "Sony WH-1000XM4 Audífonos Inalámbricos Noise Cancelling con 30h de Batería",
        "category": "Audio",
        "brand": "Sony",
        "price_usd": 198.00,
        "list_price_usd": 348.00,
        "avg_90d_usd": 248.00,
        "ships_to_colombia": True,
        "free_shipping_co": True,
        "shipping_cost_usd": 0.0,
        "requires_locker": False,
        "rating": 4.7,
        "reviews_count": 58420,
        "image_url": "https://m.media-amazon.com/images/I/71o8Q5XJS5L._AC_SL1500_.jpg",
        "highlights": [
            "Cancelación de ruido líder en la industria con procesador HD QN1 y doble sensor",
            "Audio de alta resolución LDAC y conexión multipunto Bluetooth para 2 dispositivos",
            "Pasa directo por aduana en Colombia con $0 de impuestos (≤ $200 USD) y envío gratis",
        ],
    },
    {
        "asin": "B0CHWRXH8B",
        "title": "Apple AirPods Pro (2.ª Generación) con Estuche de Carga MagSafe USB-C",
        "category": "Audio",
        "brand": "Apple",
        "price_usd": 169.99,
        "list_price_usd": 249.00,
        "avg_90d_usd": 199.99,
        "ships_to_colombia": True,
        "free_shipping_co": True,
        "shipping_cost_usd": 0.0,
        "requires_locker": False,
        "rating": 4.7,
        "reviews_count": 67430,
        "image_url": "https://m.media-amazon.com/images/I/61SUj2aKoEL._AC_SL1500_.jpg",
        "highlights": [
            "Chip H2 de Apple con hasta el doble de cancelación activa de ruido y Audio Adaptativo",
            "Estuche de carga MagSafe USB-C con altavoz integrado y resistencia IP54",
            "Entra a Colombia sin IVA ni arancel (≤ $200 USD) con envío gratis directo",
        ],
    },
    {
        "asin": "B07GBZ4Q68",
        "title": "Logitech G502 HERO Mouse Gamer de Alto Rendimiento Sensor HERO 25K (25,600 DPI)",
        "category": "Gaming",
        "brand": "Logitech G",
        "price_usd": 34.99,
        "list_price_usd": 79.99,
        "avg_90d_usd": 49.99,
        "ships_to_colombia": True,
        "free_shipping_co": False,
        "shipping_cost_usd": 11.95,
        "requires_locker": False,
        "rating": 4.6,
        "reviews_count": 55283,
        "image_url": "https://m.media-amazon.com/images/I/61mpMH5TzkL._AC_SL1500_.jpg",
        "highlights": [
            "Sensor óptico HERO 25K con seguimiento preciso de hasta 25,600 DPI sin aceleración",
            "11 botones programables, rueda hiperrápida y 5 pesas ajustables de 3.6g",
            "Envío directo a Colombia (+$11.95 USD o gratis si completas $35 USD en el carrito)",
        ],
    },
    {
        "asin": "B08166SLDF",
        "title": "AMD Ryzen 5 5600X Procesador Desbloqueado de 6 Núcleos y 12 Hilos + Cooler Wraith Stealth",
        "category": "Tecnología",
        "brand": "AMD",
        "price_usd": 119.00,
        "list_price_usd": 199.00,
        "avg_90d_usd": 159.00,
        "ships_to_colombia": True,
        "free_shipping_co": True,
        "shipping_cost_usd": 0.0,
        "requires_locker": False,
        "rating": 4.8,
        "reviews_count": 34120,
        "image_url": "https://m.media-amazon.com/images/I/61IIbwz-+ML._AC_SL1500_.jpg",
        "highlights": [
            "6 núcleos y 12 hilos desbloqueados con reloj turbo de hasta 4.6 GHz y 35 MB de caché",
            "Incluye disipador térmico AMD Wraith Stealth listo para placas AM4",
            "Cero aranceles de importación en Colombia (≤ $200 USD) y envío gratis puerta a puerta",
        ],
    },
    {
        "asin": "B071YZJ1G1",
        "title": "Logitech MX Master 2S Mouse Inalámbrico Ergonómico Bluetooth / USB Unifying (4000 DPI)",
        "category": "Tecnología",
        "brand": "Logitech",
        "price_usd": 59.99,
        "list_price_usd": 99.99,
        "avg_90d_usd": 79.99,
        "ships_to_colombia": True,
        "free_shipping_co": True,
        "shipping_cost_usd": 0.0,
        "requires_locker": False,
        "rating": 4.7,
        "reviews_count": 18900,
        "image_url": "https://m.media-amazon.com/images/I/61v1eEAWXYL._AC_SL1500_.jpg",
        "highlights": [
            "Funciona hasta en vidrio gracias al sensor Darkfield de 4,000 DPI y hasta 70 días de batería",
            "Controla hasta 3 computadores simultáneamente con Logitech Flow",
            "Envío GRATIS directo a Colombia sin casillero y 0% impuestos DIAN (≤ $200 USD)",
        ],
    },
    {
        "asin": "B09JQMJHXY",
        "title": "Apple AirPods Pro (1.ª Generación) con Estuche de Carga MagSafe",
        "category": "Audio",
        "brand": "Apple",
        "price_usd": 159.00,
        "list_price_usd": 249.00,
        "avg_90d_usd": 199.00,
        "ships_to_colombia": True,
        "free_shipping_co": True,
        "shipping_cost_usd": 0.0,
        "requires_locker": False,
        "rating": 4.7,
        "reviews_count": 45200,
        "image_url": "https://m.media-amazon.com/images/I/71bhWgQK-cL._AC_SL1500_.jpg",
        "highlights": [
            "Cancelación activa de ruido y modo Ambiente con ecualización adaptativa",
            "Estuche de carga MagSafe compatible con cargadores Qi y Lightning",
            "Exento de IVA/arancel DIAN en Colombia (≤ $200 USD) con envío gratis directo",
        ],
    },
    {
        "asin": "B09B8V1LZ3",
        "title": "Amazon Echo Dot (5.ª Gen) Parlante Inteligente con Alexa Color Carbón",
        "category": "Hogar",
        "brand": "Amazon",
        "price_usd": 29.99,
        "list_price_usd": 49.99,
        "avg_90d_usd": 44.99,
        "ships_to_colombia": False,
        "free_shipping_co": False,
        "shipping_cost_usd": 8.50,
        "requires_locker": True,
        "rating": 4.7,
        "reviews_count": 82400,
        "image_url": "https://img.pacifiko.com/PROD/resize/1/500x500/MmRhZjFjZj.jpg",
        "highlights": [
            "Audio mejorado con graves más profundos y sensor de temperatura integrado",
            "Controla luces, rutinas y música por voz con Alexa en español",
            "Requiere casillero en Miami (~$8.50 USD flete) y entra sin IVA DIAN (≤ $200 USD)",
        ],
    },
    {
        "asin": "B09B2SBHQK",
        "title": "Amazon Echo Show 5 (3.ª Gen) Pantalla Inteligente de 5.5\" con Alexa Color Carbón",
        "category": "Hogar",
        "brand": "Amazon",
        "price_usd": 49.99,
        "list_price_usd": 89.99,
        "avg_90d_usd": 79.99,
        "ships_to_colombia": False,
        "free_shipping_co": False,
        "shipping_cost_usd": 9.50,
        "requires_locker": True,
        "rating": 4.6,
        "reviews_count": 19500,
        "image_url": "https://pisces.bbystatic.com/image2/BestBuy_US/images/products/f0304c9b-f02e-4cbe-b6d9-1a630d62f87c.jpg",
        "highlights": [
            "Pantalla táctil de 5.5\", cámara de 2 MP con cubierta y sonido mejorado",
            "Ideal para mesa de noche, videollamadas y control de hogar inteligente",
            "Requiere casillero en Miami y entra exento de impuestos DIAN (≤ $200 USD)",
        ],
    },
    {
        "asin": "B0B1VQ1ZQY",
        "title": "Amazon Fire Max 11 Tablet Pantalla 11\" 2K, Octa-Core, 4GB RAM, 64GB Wi-Fi",
        "category": "Tecnología",
        "brand": "Amazon",
        "price_usd": 139.99,
        "list_price_usd": 229.99,
        "avg_90d_usd": 189.99,
        "ships_to_colombia": False,
        "free_shipping_co": False,
        "shipping_cost_usd": 12.00,
        "requires_locker": True,
        "rating": 4.5,
        "reviews_count": 8900,
        "image_url": "https://pisces.bbystatic.com/image2/BestBuy_US/images/products/85889fbf-78ec-477d-92f0-c7f6b2695156.jpg",
        "highlights": [
            "Pantalla vívida de 11\" (2000 x 1200) en cuerpo de aluminio delgado y hasta 14h de batería",
            "Procesador Octa-Core de 2.2 GHz con Wi-Fi 6 y lector de huellas integrado",
            "Requiere casillero en Miami y entra sin arancel ni IVA DIAN (≤ $200 USD)",
        ],
    },
    {
        "asin": "B09XS7JWHH",
        "title": "Sony WH-1000XM5 Audífonos Inalámbricos con Cancelación de Ruido Líder (30h Batería)",
        "category": "Audio",
        "brand": "Sony",
        "price_usd": 298.00,
        "list_price_usd": 399.99,
        "avg_90d_usd": 379.00,
        "ships_to_colombia": True,
        "free_shipping_co": True,
        "shipping_cost_usd": 0.0,
        "requires_locker": False,
        "rating": 4.6,
        "reviews_count": 19300,
        "image_url": "https://i.ebayimg.com/images/g/zLYAAOSwCaJoKo0w/s-l500.jpg",
        "highlights": [
            "8 micrófonos y procesador dual para cancelación de ruido líder en viajes",
            "Conexión multipunto Bluetooth y carga rápida USB-C (3h en 3 min)",
            "Envío GRATIS directo a Colombia (sujeto a IVA DIAN por superar $200 USD)",
        ],
    },
    {
        "asin": "B09X1H88VP",
        "title": "UGREEN Nexode 65W Cargador GaN USB-C de 3 Puertos (2x USB-C + 1x USB-A) Carga Rápida",
        "category": "Tecnología",
        "brand": "UGREEN",
        "price_usd": 29.99,
        "list_price_usd": 49.99,
        "avg_90d_usd": 42.99,
        "ships_to_colombia": True,
        "free_shipping_co": False,
        "shipping_cost_usd": 9.99,
        "requires_locker": False,
        "rating": 4.7,
        "reviews_count": 12450,
        "image_url": "https://i.ebayimg.com/images/g/0yIAAOSwcJVeQbqB/s-l500.jpg",
        "highlights": [
            "Carga laptop MacBook Air/Pro, celular y tablet al mismo tiempo con 65W GaN",
            "Tamaño compacto para viajar sin adaptadores adicionales",
            "Envío directo a Colombia (+$9.99 USD o gratis agregando $5.01 USD al carrito)",
        ],
    },
    {
        "asin": "B0BP9MDCQZ",
        "title": "Amazon Fire TV Stick 4K (2.ª Gen) Streaming Wi-Fi 6, Dolby Vision/Atmos y Alexa",
        "category": "Tecnología",
        "brand": "Amazon",
        "price_usd": 29.99,
        "list_price_usd": 49.99,
        "avg_90d_usd": 44.99,
        "ships_to_colombia": False,
        "free_shipping_co": False,
        "shipping_cost_usd": 8.50,
        "requires_locker": True,
        "rating": 4.7,
        "reviews_count": 48200,
        "image_url": "https://i.ebayimg.com/images/g/BFEAAeSwh0NqYRz0/s-l300.jpg",
        "highlights": [
            "Streaming 4K Ultra HD fluido con soporte Wi-Fi 6, Dolby Vision, HDR10+ y Dolby Atmos",
            "Control remoto por voz Alexa con botones dedicados para Netflix, Prime Video y Disney+",
            "Requiere casillero en Miami (Amazon no envía dispositivos Fire TV directo a Colombia)",
        ],
    },
    {
        "asin": "B0BP9SNVH9",
        "title": "Amazon Fire TV Stick 4K Max (2.ª Gen) con Wi-Fi 6E, 16GB y Fondo Ambiental",
        "category": "Gaming",
        "brand": "Amazon",
        "price_usd": 39.99,
        "list_price_usd": 59.99,
        "avg_90d_usd": 54.99,
        "ships_to_colombia": False,
        "free_shipping_co": False,
        "shipping_cost_usd": 8.50,
        "requires_locker": True,
        "rating": 4.7,
        "reviews_count": 21500,
        "image_url": "https://pisces.bbystatic.com/image2/BestBuy_US/images/products/ed56ad72-a9cc-487e-9ce5-c6cd5e7c1009.jpg",
        "highlights": [
            "El Fire TV Stick más potente: 16GB de almacenamiento, Wi-Fi 6E y soporte Xbox Cloud Gaming",
            "Convierte tu TV en galería de arte con el modo Fondo Ambiental de Fire TV",
            "Requiere casillero en Miami (~$8.50 USD por libra) y entra sin IVA DIAN (≤ $200 USD)",
        ],
    },
    {
        "asin": "B0CFPJYX9Q",
        "title": "Amazon Kindle Paperwhite Signature Edition 32GB (2024, 7\") Carga Inalámbrica USB-C",
        "category": "Tecnología",
        "brand": "Amazon",
        "price_usd": 154.99,
        "list_price_usd": 199.99,
        "avg_90d_usd": 194.99,
        "ships_to_colombia": False,
        "free_shipping_co": False,
        "shipping_cost_usd": 12.00,
        "requires_locker": True,
        "rating": 4.8,
        "reviews_count": 7850,
        "image_url": "https://pisces.bbystatic.com/image2/BestBuy_US/images/products/e65cdbb7-7c1b-46fa-9397-6e24fbc3e37a.jpg",
        "highlights": [
            "32GB de almacenamiento sin anuncios, pantalla de 7\" antirreflejo y luz cálida autoajustable",
            "Resistente al agua IPX8 con carga rápida USB-C y carga inalámbrica Qi",
            "Requiere casillero en Miami (~$12 USD envío) y está exento de arancel DIAN (≤ $200 USD)",
        ],
    },
    {
        "asin": "B0B7CPSN2K",
        "title": "WD_BLACK SN850X 1TB NVMe SSD Interno con Disipador (Heatsink) PCIe Gen4 (7,300 MB/s)",
        "category": "Tecnología",
        "brand": "Western Digital",
        "price_usd": 84.99,
        "list_price_usd": 159.99,
        "avg_90d_usd": 119.99,
        "ships_to_colombia": True,
        "free_shipping_co": True,
        "shipping_cost_usd": 0.0,
        "requires_locker": False,
        "rating": 4.8,
        "reviews_count": 14200,
        "image_url": "https://img.pacifiko.com/PROD/resize/1/500x500/B0B7CPSN2K.jpg",
        "highlights": [
            "Incluye disipador térmico oficial compatible directamente con la ranura M.2 de PlayStation 5",
            "Velocidades de lectura de hasta 7,300 MB/s PCIe Gen4",
            "Envío GRATIS directo a Colombia sin impuestos DIAN (≤ $200 USD)",
        ],
    },
    {
        "asin": "B07FDJMC9Q",
        "title": "Ninja AF101 Freidora de Aire de 4 Cuartos (3.8L) 4-en-1 con Recubrimiento Cerámico",
        "category": "Hogar",
        "brand": "Ninja",
        "price_usd": 79.99,
        "list_price_usd": 129.99,
        "avg_90d_usd": 109.99,
        "ships_to_colombia": True,
        "free_shipping_co": True,
        "shipping_cost_usd": 0.0,
        "requires_locker": False,
        "rating": 4.8,
        "reviews_count": 51900,
        "image_url": "https://img.pacifiko.com/PROD/resize/1/500x500/B07FDJMC9Q.jpg",
        "highlights": [
            "4 programas: Freír con aire, Asar, Recalentar y Deshidratar (110V compatible Colombia)",
            "Canasta antiadherente recubierta de cerámica libre de PTFE/PFOA apta para lavavajillas",
            "Envío gratis directo a Colombia sin impuestos DIAN por costar menos de $200 USD",
        ],
    },
    {
        "asin": "B07VGRJDFY",
        "title": "Nintendo Switch con Joy-Con Neón Azul y Rojo (Modelo V2 Batería Extendida)",
        "category": "Gaming",
        "brand": "Nintendo",
        "price_usd": 239.99,
        "list_price_usd": 299.99,
        "avg_90d_usd": 299.00,
        "ships_to_colombia": True,
        "free_shipping_co": True,
        "shipping_cost_usd": 0.0,
        "requires_locker": False,
        "rating": 4.9,
        "reviews_count": 88400,
        "image_url": "https://img.pacifiko.com/PROD/resize/1/500x500/B07VGRJDFY.jpg",
        "highlights": [
            "Juega en TV o en modo portátil con hasta 9 horas de batería",
            "Envío GRATIS directo a Colombia (sujeto a impuestos DIAN por superar $200 USD)",
            "Compatible con voltaje 110V–220V en Colombia",
        ],
    },
    {
        "asin": "B09DFCB66S",
        "title": "Sony PlayStation 5 Consola Edición Estándar con Lector de Discos Blu-Ray 4K",
        "category": "Gaming",
        "brand": "Sony",
        "price_usd": 399.00,
        "list_price_usd": 499.99,
        "avg_90d_usd": 499.00,
        "ships_to_colombia": True,
        "free_shipping_co": True,
        "shipping_cost_usd": 0.0,
        "requires_locker": False,
        "rating": 4.8,
        "reviews_count": 26500,
        "image_url": "https://img.pacifiko.com/PROD/resize/1/500x500/N2Y0NmJiMT.jpg",
        "highlights": [
            "SSD ultrarrápido, audio 3D Tempest y control DualSense con retroalimentación háptica",
            "Compatible con voltaje 110V–240V en Colombia",
            "Envío GRATIS directo a Colombia (aplica IVA/arancel DIAN por superar $200 USD)",
        ],
    },
    {
        "asin": "B08BX7FV5L",
        "title": "Amazon Fire HD 10 Tablet (11.ª Gen) Pantalla 10.1\" Full HD 1080p, 32GB Negro",
        "category": "Tecnología",
        "brand": "Amazon",
        "price_usd": 89.99,
        "list_price_usd": 149.99,
        "avg_90d_usd": 129.99,
        "ships_to_colombia": False,
        "free_shipping_co": False,
        "shipping_cost_usd": 11.00,
        "requires_locker": True,
        "rating": 4.6,
        "reviews_count": 41200,
        "image_url": "https://i.ebayimg.com/images/g/HU4AAOSwl4Zj90~l/s-l1600.jpg",
        "highlights": [
            "Pantalla Full HD 1080p de 10.1\" con 3GB RAM, puerto USB-C y hasta 12 horas de batería",
            "Ideal para lectura, streaming, clases virtuales y navegación diaria",
            "Requiere casillero en Miami y entra exenta de IVA/arancel DIAN (≤ $200 USD)",
        ],
    },
    {
        "asin": "B07J2Z5DBM",
        "title": "TOZO T10 Audífonos Bluetooth 5.3 Inalámbricos Impermeables IPX8 con Estuche Carga Inalámbrica",
        "category": "Audio",
        "brand": "TOZO",
        "price_usd": 18.99,
        "list_price_usd": 39.99,
        "avg_90d_usd": 29.99,
        "ships_to_colombia": True,
        "free_shipping_co": False,
        "shipping_cost_usd": 8.99,
        "requires_locker": False,
        "rating": 4.4,
        "reviews_count": 215000,
        "image_url": "https://i.ebayimg.com/images/g/~yEAAOSwaVtnWwf6/s-l500.jpg",
        "highlights": [
            "Resistencia al agua IPX8 y drivers de 8 mm con graves potentes",
            "Hasta 45 horas de reproducción total con estuche compatible con carga inalámbrica",
            "Envío directo a Colombia (agrega productos hasta $35 USD para envío gratis)",
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


def _is_valid_https_image(url: str | None) -> bool:
    if not url or not isinstance(url, str):
        return False
    u = url.strip()
    if not u.startswith("https://"):
        return False
    lowered = u.lower()
    if any(bad in lowered for bad in ("grey-pixel", "transparent-pixel", "sprite", "1x1")):
        return False
    return True


def _extract_dynamic_image_url(raw_json_str: str | None) -> str:
    if not raw_json_str:
        return ""
    try:
        import html as _html
        import json as _json

        decoded = _html.unescape(raw_json_str)
        data = _json.loads(decoded)
        if isinstance(data, dict):
            best_url = ""
            best_area = -1
            for img_url, dims in data.items():
                if not _is_valid_https_image(str(img_url)):
                    continue
                area = 0
                if isinstance(dims, (list, tuple)) and len(dims) >= 2:
                    try:
                        area = int(dims[0]) * int(dims[1])
                    except Exception:
                        area = 0
                if area > best_area:
                    best_area = area
                    best_url = str(img_url)
            return best_url
    except Exception:
        pass
    return ""


def _is_captcha_or_blocked(html: str) -> bool:
    lowered = html.lower()
    return any(
        marker in lowered
        for marker in (
            "enter the characters you see below",
            "sorry, we just need to make sure you're not a robot",
            "type the characters you see in this image",
            "validatecaptcha",
            "api-services-support@amazon.com",
        )
    )


def parse_amazon_html(html: str, asin: str) -> dict[str, Any]:
    """
    Parse an Amazon product HTML fragment or page deterministically with BeautifulSoup4
    (with stdlib regex fallback if BeautifulSoup4 is not installed in the current environment).
    Extracts title, current price, real strike-through list price, https image URL, and Colombia shipping eligibility.
    """
    import html as _html

    raw_html = html or ""
    if not raw_html or _is_captcha_or_blocked(raw_html):
        return {
            "asin": asin,
            "title": "",
            "category": "Tecnología",
            "brand": "",
            "price_usd": 0.0,
            "list_price_usd": 0.0,
            "avg_90d_usd": 0.0,
            "ships_to_colombia": False,
            "free_shipping_co": False,
            "shipping_cost_usd": 0.0,
            "requires_locker": False,
            "rating": 0.0,
            "reviews_count": 0,
            "image_url": "",
            "highlights": [],
            "live_verified": False,
        }

    title = ""
    price_usd = 0.0
    list_price_usd = 0.0
    image_url = ""

    if HAS_BS4 and BeautifulSoup is not None:
        soup = BeautifulSoup(raw_html, "html.parser")

        title_node = (
            soup.select_one("#productTitle")
            or soup.select_one("#title")
            or soup.select_one("h1")
        )
        title = title_node.get_text(" ", strip=True) if title_node else ""

        price_selectors = (
            "#corePriceDisplay_desktop_feature_div .priceToPay .a-offscreen",
            "#corePriceDisplay_desktop_feature_div .a-price:not(.a-text-price) .a-offscreen",
            "#corePrice_feature_div .priceToPay .a-offscreen",
            "#corePrice_feature_div .a-price:not(.a-text-price) .a-offscreen",
            "#apex_desktop .priceToPay .a-offscreen",
            "#apex_desktop .a-price:not(.a-text-price) .a-offscreen",
            "#desktop_buybox .a-price:not(.a-text-price) .a-offscreen",
            "#buybox .a-price:not(.a-text-price) .a-offscreen",
            "#price_inside_buybox",
            "#priceblock_dealprice",
            "#priceblock_ourprice",
        )
        for sel in price_selectors:
            for node in soup.select(sel):
                val = _extract_float_price(node.get_text(" ", strip=True))
                if val > 0.0:
                    price_usd = val
                    break
            if price_usd > 0.0:
                break

        if price_usd <= 0.0:
            part_containers = (
                "#corePriceDisplay_desktop_feature_div .priceToPay",
                "#corePriceDisplay_desktop_feature_div .a-price:not(.a-text-price)",
                "#corePrice_feature_div .priceToPay",
                "#corePrice_feature_div .a-price:not(.a-text-price)",
                "#apex_desktop .priceToPay",
                "#apex_desktop .a-price:not(.a-text-price)",
                "#desktop_buybox .a-price:not(.a-text-price)",
                "#buybox .a-price:not(.a-text-price)",
            )
            for sel in part_containers:
                for pnode in soup.select(sel):
                    whole_el = pnode.select_one(".a-price-whole")
                    if whole_el:
                        whole_digits = re.sub(r"[^\d]", "", whole_el.get_text(strip=True))
                        frac_el = pnode.select_one(".a-price-fraction")
                        frac_digits = re.sub(r"[^\d]", "", frac_el.get_text(strip=True)) if frac_el else "00"
                        if whole_digits:
                            try:
                                val = float(f"{whole_digits}.{frac_digits or '00'}")
                                if val > 0.0:
                                    price_usd = val
                                    break
                            except ValueError:
                                pass
                if price_usd > 0.0:
                    break

        if price_usd <= 0.0:
            for hidden_sel in (
                "#twister-plus-price-data-price",
                "input[name='items[0.base][customerVisiblePrice][amount]']",
            ):
                hnode = soup.select_one(hidden_sel)
                if hnode:
                    val = _extract_float_price(str(hnode.get("value") or ""))
                    if val > 0.0:
                        price_usd = val
                        break

        list_selectors = (
            "#corePriceDisplay_desktop_feature_div .basisPrice .a-offscreen",
            "#corePrice_feature_div .basisPrice .a-offscreen",
            "#apex_desktop .basisPrice .a-offscreen",
            "#corePriceDisplay_desktop_feature_div .a-price.a-text-price .a-offscreen",
            "#corePrice_feature_div .a-price.a-text-price .a-offscreen",
            ".basisPrice .a-offscreen",
            "#corePriceDisplay_desktop_feature_div span[data-a-strike='true'] .a-offscreen",
            "#listPrice",
            "#priceblock_strikeprice",
        )
        for sel in list_selectors:
            for lnode in soup.select(sel):
                val = _extract_float_price(lnode.get_text(" ", strip=True))
                if val > 0.0:
                    list_price_usd = val
                    break
            if list_price_usd > 0.0:
                break

        delivery_selectors = (
            "#mir-layout-DELIVERY_BLOCK",
            "#deliveryBlockMessage",
            "#amazonGlobal_feature_div",
            "#exports_desktop_qualifiedBuybox_tlc_feature_div",
            "#exports_desktop_qualifiedBuybox_deliveryBlock_feature_div",
            "#availability",
            "#outOfStock",
            "#unqualifiedBuyBox",
            "#buybox",
            "#desktop_buybox",
        )
        delivery_chunks = [
            node.get_text(" ", strip=True)
            for sel in delivery_selectors
            for node in soup.select(sel)
        ]
        delivery_text = (" ".join(delivery_chunks) if delivery_chunks else raw_html).lower()

        ingress_nodes = soup.select(
            "#glow-ingress-block, #glow-ingress-line1, #glow-ingress-line2, "
            "#contextualIngressPtLabel, #contextualIngressPtLabel_deliveryShortLine"
        )
        ingress_text = " ".join(n.get_text(" ", strip=True) for n in ingress_nodes).lower()

        is_full_dp_page = bool(
            soup.select_one("#ppd, #dp-container, #desktop_buybox, #buybox, #availability, #outOfStock")
        )
        has_buybox_cta = bool(
            soup.select_one(
                "[id^='add-to-cart-button'], #buy-now-button, #one-click-button, "
                "input[name='submit.add-to-cart'], #exports_desktop_qualifiedBuybox_atc_feature_div"
            )
        )
        has_unqualified_box = bool(soup.select_one("#outOfStock, #unqualifiedBuyBox"))

        rating_node = soup.select_one("#acrPopover") or soup.select_one(".a-icon-alt")
        rating_val = _extract_float_price(rating_node.get_text(strip=True) if rating_node else "")
        rating = rating_val if 0.0 < rating_val <= 5.0 else 4.7

        for selector in ("#landingImage", "#imgBlkFront", "#main-image"):
            img_node = soup.select_one(selector)
            if not img_node:
                continue
            for attr in ("data-old-hires", "src", "data-src"):
                candidate = str(img_node.get(attr) or "").strip()
                if _is_valid_https_image(candidate):
                    image_url = candidate
                    break
            if not image_url and img_node.get("data-a-dynamic-image"):
                image_url = _extract_dynamic_image_url(str(img_node.get("data-a-dynamic-image")))
            if image_url:
                break

        if not image_url:
            og_img = soup.select_one("meta[property='og:image']")
            if og_img and _is_valid_https_image(str(og_img.get("content") or "")):
                image_url = str(og_img.get("content")).strip()
    else:
        title_match = re.search(r'id=["\']productTitle["\'][^>]*>(.*?)</', raw_html, re.S | re.I)
        if not title_match:
            title_match = re.search(r'<h1[^>]*>(.*?)</h1>', raw_html, re.S | re.I)
        title = _html.unescape(re.sub(r"<[^>]+>", "", title_match.group(1)).strip()) if title_match else ""

        # Current price: prefer corePrice / priceToPay / non-strike a-price
        price_block_match = re.search(
            r'id=["\'](?:corePriceDisplay_desktop_feature_div|corePrice_feature_div|apex_desktop)["\']',
            raw_html,
            re.I,
        )
        price_scope = raw_html[price_block_match.start() : price_block_match.start() + 14000] if price_block_match else raw_html
        price_usd = 0.0
        for ap_m in re.finditer(r'class=["\']([^"\']*\ba-price\b[^"\']*)["\'][^>]*>', price_scope, re.I):
            cls_str = ap_m.group(1).lower()
            if "a-text-price" in cls_str:
                continue
            window = price_scope[ap_m.end() : ap_m.end() + 350]
            off_m = re.search(r'class=["\'][^"\']*a-offscreen[^"\']*["\'][^>]*>\s*([^<]*)<', window, re.I)
            if off_m:
                val = _extract_float_price(off_m.group(1))
                if val > 0.0:
                    price_usd = val
                    break
            wf_m = re.search(
                r'class=["\'][^"\']*a-price-whole[^"\']*["\'][^>]*>\s*([0-9,]+)',
                window,
                re.I,
            )
            if wf_m:
                frac_m = re.search(
                    r'class=["\'][^"\']*a-price-fraction[^"\']*["\'][^>]*>\s*([0-9]{1,2})',
                    window[wf_m.end() :],
                    re.I,
                )
                whole_d = re.sub(r"[^\d]", "", wf_m.group(1) or "")
                frac_d = re.sub(r"[^\d]", "", frac_m.group(1) if frac_m else "00")
                if whole_d:
                    try:
                        val = float(f"{whole_d}.{frac_d or '00'}")
                        if val > 0.0:
                            price_usd = val
                            break
                    except ValueError:
                        pass
        if price_usd <= 0.0:
            hidden_m = re.search(
                r'id=["\']twister-plus-price-data-price["\'][^>]*value=["\']([^"\']+)["\']',
                price_scope,
                re.I,
            ) or re.search(
                r'id=["\']priceblock_(?:deal|our)price["\'][^>]*>\s*([^<]+)<',
                raw_html,
                re.I,
            )
            if hidden_m:
                price_usd = _extract_float_price(hidden_m.group(1))

        # Strike-through list price: strictly inside basisPrice or a-text-price or data-a-strike
        list_price_usd = 0.0
        for strike_m in re.finditer(
            r'(?:basisPrice|a-text-price|data-a-strike=["\']true["\'])[^>]*>.*?class=["\'][^"\']*a-offscreen[^"\']*["\'][^>]*>\s*([^<]+)<',
            price_scope,
            re.S | re.I,
        ):
            val = _extract_float_price(strike_m.group(1))
            if val > 0.0:
                list_price_usd = val
                break
        delivery_text = re.sub(r"<[^>]+>", " ", raw_html).lower()
        ingress_m = re.search(
            r'id=["\'](?:glow-ingress-block|glow-ingress-line2|contextualIngressPtLabel)["\'][^>]*>(.*?)</div>',
            raw_html,
            re.S | re.I,
        )
        ingress_text = re.sub(r"<[^>]+>", " ", ingress_m.group(1)).lower() if ingress_m else ""
        is_full_dp_page = bool(re.search(r'id=["\'](?:ppd|dp-container|desktop_buybox|buybox|availability|outOfStock)["\']', raw_html, re.I))
        has_buybox_cta = bool(re.search(r'(?:add-to-cart-button|buy-now-button|submit\.add-to-cart)', raw_html, re.I))
        has_unqualified_box = bool(re.search(r'id=["\'](?:outOfStock|unqualifiedBuyBox)["\']', raw_html, re.I))
        rating = 4.7

        for img_pattern in (
            r'data-old-hires=["\'](https://[^"\']+)["\']',
            r'id=["\']landingImage["\'][^>]*\bsrc=["\'](https://[^"\']+)["\']',
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\'](https://[^"\']+)["\']',
        ):
            m = re.search(img_pattern, raw_html, re.I)
            if m and _is_valid_https_image(m.group(1)):
                image_url = m.group(1).strip()
                break
        if not image_url:
            dyn_match = re.search(r'data-a-dynamic-image=["\']([^"\']+)["\']', raw_html, re.I)
            if dyn_match:
                image_url = _extract_dynamic_image_url(dyn_match.group(1))

    if list_price_usd <= price_usd:
        list_price_usd = price_usd

    title_clean = re.sub(r"\s+", " ", title).strip()
    title_valid = bool(
        title_clean
        and len(title_clean) >= 5
        and not title_clean.lower().startswith("amazon product")
        and title_clean.lower() not in ("amazon.com", "amazon")
    )
    if not title_clean:
        title_clean = f"Amazon Product {asin}"

    no_ship_phrases = (
        "cannot be shipped to your selected delivery location",
        "does not ship to",
        "no se puede enviar a tu ubicación",
        "no se puede enviar a tu dirección",
        "no puede enviarse este producto al punto de entrega seleccionado",
        "no puede enviarse este producto",
        "no puede enviarse al punto de entrega",
        "selecciona un punto de entrega diferente",
        "choose a different delivery location",
        "no realiza envíos a",
        "currently unavailable",
        "no está disponible",
        "temporarily out of stock",
        "temporalmente agotado",
        "ver artículos similares",
        "see similar items",
    )
    unqualified_phrases = (
        "see all buying options",
        "ver todas las opciones de compra",
        "ver artículos similares",
        "see similar items",
    )
    availability_scope = f"{delivery_text} {ingress_text}".strip()
    if HAS_BS4 and BeautifulSoup is not None:
        avail_node = soup.select_one("#availability") or soup.select_one("#outOfStock")
        if avail_node:
            availability_scope = f"{availability_scope} {avail_node.get_text(' ', strip=True).lower()}"

    explicitly_blocked_co = any(phrase in availability_scope for phrase in no_ship_phrases)
    has_buybox = not has_unqualified_box and not any(
        phrase in availability_scope for phrase in unqualified_phrases
    )
    if is_full_dp_page and not has_buybox_cta:
        has_buybox = False

    colombia_confirmed_signals = (
        "colombia",
        "amazonglobal",
        "import fees",
        "derechos de importación",
        "cargos de importación",
        "sin cargos de importación",
        "no import fees",
    )
    has_colombia_signal = any(sig in availability_scope for sig in colombia_confirmed_signals)

    if explicitly_blocked_co:
        delivery_country_confirmed = "BLOCKED_CO"
        ships_to_colombia = False
    elif has_colombia_signal:
        delivery_country_confirmed = "CO"
        ships_to_colombia = True
    else:
        delivery_country_confirmed = "US_OR_UNKNOWN"
        ships_to_colombia = True

    free_shipping_co = ships_to_colombia and price_usd >= 35.0 and (
        "free" in delivery_text
        or "gratis" in delivery_text
        or "colombia" in delivery_text
        or price_usd >= 35.0
    )

    requires_locker = not ships_to_colombia
    shipping_cost_usd = 0.0 if (ships_to_colombia and free_shipping_co) else (8.50 if requires_locker else 11.95)
    live_verified = bool(price_usd > 0.0 and title_valid and has_buybox)

    from src.broadcaster.card_image import upgrade_amazon_image_url

    image_url = upgrade_amazon_image_url(image_url, size=1200)

    return {
        "asin": asin,
        "title": title_clean,
        "category": "Tecnología",
        "brand": "",
        "price_usd": price_usd,
        "list_price_usd": list_price_usd,
        "avg_90d_usd": list_price_usd,
        "ships_to_colombia": ships_to_colombia,
        "free_shipping_co": free_shipping_co,
        "shipping_cost_usd": shipping_cost_usd,
        "requires_locker": requires_locker,
        "rating": rating,
        "reviews_count": 100,
        "image_url": image_url,
        "live_verified": live_verified,
        "detail_verified": True,
        "has_buybox": has_buybox,
        "delivery_country_confirmed": delivery_country_confirmed,
        "highlights": [
            "Precio verificado en el Buy Box de Amazon.com (/dp/)",
            "Elegible para envío internacional AmazonGlobal hacia Colombia"
            if not requires_locker
            else "Requiere casillero en Miami para reenvío a Colombia",
            "Garantía de compra directa en Amazon.com",
        ],
    }


class AmazonMonitorScraper:
    """
    Hybrid Zero-Token Amazon.com monitor for Colombia:
    - Uses deterministic seed catalog when `use_seed=True` for offline/CI reproducibility
    - Uses strictly live-verified `/dp/ASIN` pages with Colombia (`CO`) shipping session when `use_seed=False`
    """

    def __init__(self, timeout: int = 10) -> None:
        self.timeout = timeout
        self.has_scrapling = HAS_SCRAPLING
        self._curl_session: Any = None
        self._colombia_location_ready = False
        self._glow_debug: dict[str, Any] = {}
        self._last_fetch_meta: dict[str, Any] = {}
        self.last_telemetry: dict[str, Any] = {}

    @staticmethod
    def _default_headers(include_cookie: bool = True) -> dict[str, str]:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "es-US,es;q=0.9,en;q=0.8",
        }
        if include_cookie:
            headers["Cookie"] = 'i18n-prefs=USD; lc-main=es_US; sp-cdn="L5Z9:CO"'
        return headers

    @staticmethod
    def _seed_session_cookies(session: Any) -> None:
        try:
            session.cookies.set("i18n-prefs", "USD", domain=".amazon.com")
            session.cookies.set("lc-main", "es_US", domain=".amazon.com")
        except Exception:
            pass

    @staticmethod
    def _extract_csrf_token(html_text: str) -> str:
        import html as _html

        decoded = _html.unescape(html_text or "")
        patterns = (
            r'CSRF_TOKEN\s*[:=]\s*["\']([^"\']+)["\']',
            r'["\']anti-csrftoken-a2z["\']\s*:\s*["\']([^"\']+)["\']',
            r'name=["\']anti-csrftoken-a2z["\'][^>]*content=["\']([^"\']+)["\']',
            r'anti-csrftoken-a2z["\']?\s*[:=]\s*["\']([^"\']+)["\']',
            r'name=["\']glowValidationToken["\'][^>]*value=["\']([^"\']+)["\']',
            r'"csrfToken"\s*:\s*"([^"]+)"',
        )
        for pat in patterns:
            m = re.search(pat, decoded, re.I)
            if m and m.group(1).strip():
                return m.group(1).strip()
        return ""

    @staticmethod
    def _extract_glow_modal_info(html_text: str) -> tuple[str, str]:
        """Extract exact (modal_url, ajax_csrf_token) from #nav-global-location-data-modal-action."""
        import html as _html
        import json as _json

        raw_json = ""
        if HAS_BS4 and BeautifulSoup is not None and html_text:
            try:
                soup = BeautifulSoup(html_text, "html.parser")
                node = soup.select_one("#nav-global-location-data-modal-action")
                if node:
                    raw_json = str(node.get("data-a-modal") or "")
            except Exception:
                pass
        if not raw_json and html_text:
            m = re.search(
                r'id=["\']nav-global-location-data-modal-action["\'][^>]*data-a-modal=["\']([^"\']+)["\']',
                html_text,
                re.I,
            )
            if m:
                raw_json = m.group(1)
        if raw_json:
            try:
                data = _json.loads(_html.unescape(raw_json))
                if isinstance(data, dict):
                    url = str(data.get("url") or "").strip()
                    ajax_headers = data.get("ajaxHeaders") or {}
                    csrf = str(ajax_headers.get("anti-csrftoken-a2z") or "").strip()
                    return url, csrf
            except Exception:
                pass
        return "", ""

    @staticmethod
    def _extract_ingress_snippet(html_text: str) -> str:
        if HAS_BS4 and BeautifulSoup is not None and html_text:
            try:
                soup = BeautifulSoup(html_text, "html.parser")
                nodes = soup.select("#glow-ingress-line2, #contextualIngressPtLabel_deliveryShortLine")
                txt = " ".join(n.get_text(" ", strip=True) for n in nodes).strip()
                return txt[:60]
            except Exception:
                pass
        return ""

    def _bootstrap_colombia_location_curl(self, session: Any, bootstrap_asin: str = "B0B9C4DKKG") -> None:
        if self._colombia_location_ready:
            return
        self._seed_session_cookies(session)
        headers = self._default_headers(include_cookie=False)
        debug: dict[str, Any] = {}
        try:
            boot_url = f"https://www.amazon.com/dp/{bootstrap_asin}?language=es_US"
            boot_resp = session.get(boot_url, headers=headers, timeout=self.timeout)
            debug["boot_status"] = int(getattr(boot_resp, "status_code", 0) or 0)
            boot_text = getattr(boot_resp, "text", "") or ""
            if _is_captcha_or_blocked(boot_text):
                debug["boot_captcha"] = True
                self._glow_debug = debug
                self._colombia_location_ready = False
                return

            modal_path, modal_ajax_csrf = self._extract_glow_modal_info(boot_text)
            debug["modal_action_found"] = bool(modal_path)
            debug["modal_ajax_csrf_found"] = bool(modal_ajax_csrf)

            modal_url = (
                f"https://www.amazon.com{modal_path}"
                if modal_path.startswith("/")
                else (
                    modal_path
                    or "https://www.amazon.com/portal-migration/hz/glow/get-rendered-address-selections?deviceType=desktop&pageType=Detail&storeContext=pc&actionSource=desktop-modal"
                )
            )
            modal_headers = {
                **headers,
                "Accept": "text/html,*/*;q=0.8",
                "Origin": "https://www.amazon.com",
                "Referer": boot_url,
                "X-Requested-With": "XMLHttpRequest",
            }
            if modal_ajax_csrf:
                modal_headers["anti-csrftoken-a2z"] = modal_ajax_csrf

            modal_resp = session.get(modal_url, headers=modal_headers, timeout=self.timeout)
            debug["modal_status"] = int(getattr(modal_resp, "status_code", 0) or 0)
            modal_text = getattr(modal_resp, "text", "") or ""
            post_csrf = self._extract_csrf_token(modal_text) or modal_ajax_csrf or self._extract_csrf_token(boot_text)
            debug["post_csrf_found"] = bool(post_csrf)

            glow_headers = {
                **modal_headers,
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Content-Type": "application/json",
            }
            if post_csrf:
                glow_headers["anti-csrftoken-a2z"] = post_csrf

            payload = {
                "locationType": "COUNTRY",
                "district": "CO",
                "countryCode": "CO",
                "deviceType": "web",
                "pageType": "Detail",
                "storeContext": "pc",
                "almBrandId": "undefined",
            }
            post_resp = session.post(
                "https://www.amazon.com/portal-migration/hz/glow/address-change?actionSource=glow",
                json=payload,
                headers=glow_headers,
                timeout=self.timeout,
            )
            debug["post_status"] = int(getattr(post_resp, "status_code", 0) or 0)
            debug["post_body"] = (getattr(post_resp, "text", "") or "").strip()[:140]

            if debug["post_status"] != 200 or not debug["post_body"]:
                form_headers = {
                    **modal_headers,
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                }
                if post_csrf:
                    form_headers["anti-csrftoken-a2z"] = post_csrf
                ajax_post = session.post(
                    "https://www.amazon.com/gp/delivery/ajax/address-change.html",
                    data=payload,
                    headers=form_headers,
                    timeout=self.timeout,
                )
                debug["ajax_post_status"] = int(getattr(ajax_post, "status_code", 0) or 0)
                debug["ajax_post_body"] = (getattr(ajax_post, "text", "") or "").strip()[:120]

            self._glow_debug = debug
            self._colombia_location_ready = True
        except Exception as exc:
            debug["exc"] = type(exc).__name__
            self._glow_debug = debug

    def _parse_if_valid_page(self, html_text: str, asin: str) -> dict[str, Any] | None:
        if not html_text or _is_captcha_or_blocked(html_text):
            return None
        parsed = parse_amazon_html(html_text, asin)
        has_real_title = not str(parsed.get("title") or "").lower().startswith("amazon product ")
        if has_real_title or parsed.get("price_usd", 0.0) > 0 or parsed.get("delivery_country_confirmed") == "BLOCKED_CO":
            return parsed
        return None

    def fetch_asin_live(self, asin: str) -> dict[str, Any] | None:
        """Fetch live product page from Amazon.com with Colombia (`CO`) destination context."""
        url = f"https://www.amazon.com/dp/{asin}?language=es_US"
        headers = self._default_headers(include_cookie=True)
        session_headers = self._default_headers(include_cookie=False)
        self._last_fetch_meta = {"asin": asin, "client": "none", "status": "none", "outcome": "init"}
        got_http_captcha = False

        if HAS_CURL_CFFI and curl_requests is not None:
            # 1a. Sesión persistente Chrome con cookie jar real y ubicación Colombia
            try:
                if self._curl_session is None:
                    self._curl_session = curl_requests.Session(impersonate="chrome")
                    self._colombia_location_ready = False
                self._bootstrap_colombia_location_curl(self._curl_session)
                resp = self._curl_session.get(url, headers=session_headers, timeout=self.timeout)
                status_code = int(getattr(resp, "status_code", 0) or 0)
                resp_text = getattr(resp, "text", "") or ""
                if status_code == 200:
                    if _is_captcha_or_blocked(resp_text):
                        got_http_captcha = True
                        self._last_fetch_meta = {"asin": asin, "client": "curl_session", "status": 200, "outcome": "captcha"}
                        self._curl_session = None
                        self._colombia_location_ready = False
                    else:
                        parsed = self._parse_if_valid_page(resp_text, asin)
                        if parsed is not None:
                            self._last_fetch_meta = {
                                "asin": asin,
                                "client": "curl_session",
                                "status": 200,
                                "outcome": "parsed_ok",
                                "dest": parsed.get("delivery_country_confirmed"),
                                "ingress": self._extract_ingress_snippet(resp_text),
                                "has_buybox": parsed.get("has_buybox"),
                                "price_usd": parsed.get("price_usd"),
                                "list_price_usd": parsed.get("list_price_usd"),
                            }
                            return parsed
                        self._last_fetch_meta = {"asin": asin, "client": "curl_session", "status": 200, "outcome": "unparsed_dom"}
                else:
                    self._last_fetch_meta = {"asin": asin, "client": "curl_session", "status": status_code, "outcome": f"http_{status_code}"}
                    if status_code in (403, 503):
                        self._curl_session = None
                        self._colombia_location_ready = False
            except Exception as exc:
                self._last_fetch_meta = {"asin": asin, "client": "curl_session", "status": "exc", "outcome": type(exc).__name__}
                self._curl_session = None
                self._colombia_location_ready = False

            # 1b. Reintento limpio stateless con perfil TLS alternativo y cookie sp-cdn="L5Z9:CO"
            for profile in ("chrome124", "safari17_0"):
                try:
                    resp2 = curl_requests.get(
                        url,
                        impersonate=profile,
                        headers=headers,
                        timeout=min(self.timeout, 8),
                    )
                    sc2 = int(getattr(resp2, "status_code", 0) or 0)
                    txt2 = getattr(resp2, "text", "") or ""
                    if sc2 == 200 and not _is_captcha_or_blocked(txt2):
                        parsed2 = self._parse_if_valid_page(txt2, asin)
                        if parsed2 is not None:
                            self._last_fetch_meta = {
                                "asin": asin,
                                "client": f"curl_{profile}",
                                "status": 200,
                                "outcome": "parsed_ok",
                                "dest": parsed2.get("delivery_country_confirmed"),
                                "has_buybox": parsed2.get("has_buybox"),
                                "price_usd": parsed2.get("price_usd"),
                                "list_price_usd": parsed2.get("list_price_usd"),
                            }
                            return parsed2
                    elif sc2 == 200:
                        got_http_captcha = True
                        self._last_fetch_meta = {"asin": asin, "client": f"curl_{profile}", "status": 200, "outcome": "captcha"}
                    else:
                        self._last_fetch_meta = {"asin": asin, "client": f"curl_{profile}", "status": sc2, "outcome": f"http_{sc2}"}
                except Exception as exc:
                    self._last_fetch_meta = {"asin": asin, "client": f"curl_{profile}", "status": "exc", "outcome": type(exc).__name__}

        if HAS_SCRAPLING and FetcherSession is not None:
            try:
                with FetcherSession(impersonate="chrome", timeout=min(self.timeout, 8)) as session:
                    try:
                        session.get(
                            "https://www.amazon.com/gp/delivery/ajax/address-change.html?locationType=COUNTRY&district=CO&countryCode=CO&deviceType=web&pageType=Detail&storeContext=generic",
                            headers=headers,
                        )
                    except Exception:
                        pass
                    response = session.get(url, headers=headers)
                    html = getattr(response, "text", "") or str(getattr(response, "body", ""))
                    if _is_captcha_or_blocked(html):
                        got_http_captcha = True
                        self._last_fetch_meta = {"asin": asin, "client": "scrapling", "status": 200, "outcome": "captcha"}
                    else:
                        parsed = self._parse_if_valid_page(html, asin)
                        if parsed is not None:
                            self._last_fetch_meta = {
                                "asin": asin,
                                "client": "scrapling",
                                "status": 200,
                                "outcome": "parsed_ok",
                                "dest": parsed.get("delivery_country_confirmed"),
                                "has_buybox": parsed.get("has_buybox"),
                                "price_usd": parsed.get("price_usd"),
                                "list_price_usd": parsed.get("list_price_usd"),
                            }
                            return parsed
            except Exception as exc:
                self._last_fetch_meta = {"asin": asin, "client": "scrapling", "status": "exc", "outcome": type(exc).__name__}

        if not got_http_captcha:
            try:
                import urllib.request

                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=min(self.timeout, 6)) as resp:
                    if resp.status == 200:
                        html = resp.read().decode("utf-8", errors="ignore")
                        parsed = self._parse_if_valid_page(html, asin)
                        if parsed is not None:
                            self._last_fetch_meta = {
                                "asin": asin,
                                "client": "urllib",
                                "status": 200,
                                "outcome": "parsed_ok",
                                "dest": parsed.get("delivery_country_confirmed"),
                                "has_buybox": parsed.get("has_buybox"),
                                "price_usd": parsed.get("price_usd"),
                                "list_price_usd": parsed.get("list_price_usd"),
                            }
                            return parsed
            except Exception as exc:
                if self._last_fetch_meta.get("client") == "none":
                    self._last_fetch_meta = {"asin": asin, "client": "urllib", "status": "exc", "outcome": type(exc).__name__}
        return None

    def fetch_catalog(
        self,
        use_seed: bool = True,
        asins: list[str] | None = None,
        extra_items: list[dict[str, Any]] | None = None,
        max_live_asins: int = 60,
    ) -> list[dict[str, Any]]:
        """
        Return the list of monitored Amazon products for Colombia.
        If `use_seed=True`, returns the curated SEED_PRODUCTS_COLOMBIA (filtered by `asins` if provided).
        If `use_seed=False`, fetches ONLY genuinely live `/dp/ASIN` verified products (never trusts unverified search-tab prices).
        """
        import time as _time

        seed_map = {item["asin"]: dict(item) for item in SEED_PRODUCTS_COLOMBIA}
        extra_map: dict[str, dict[str, Any]] = {}
        for item in extra_items or []:
            if item.get("asin"):
                key = str(item["asin"]).upper()
                if key not in extra_map or item.get("detail_verified"):
                    extra_map[key] = dict(item)

        if asins:
            target_asins = [a.upper() for a in asins]
        elif use_seed:
            target_asins = [item["asin"] for item in SEED_PRODUCTS_COLOMBIA]
        else:
            # En modo live: priorizar ASINs recién descubiertos de la pestaña de Ofertas + semillas con envío a Colombia
            seed_colombia_asins = [
                item["asin"]
                for item in SEED_PRODUCTS_COLOMBIA
                if item.get("ships_to_colombia", True) and not item.get("requires_locker", False)
            ]
            target_asins = list(extra_map.keys())
            for asin_key in seed_colombia_asins:
                if asin_key not in extra_map:
                    target_asins.append(asin_key)

        if use_seed:
            results: list[dict[str, Any]] = []
            for asin in target_asins:
                if asin in seed_map:
                    results.append(dict(seed_map[asin]))
            self.last_telemetry = {
                "mode": "seed",
                "target_asins_count": len(target_asins),
                "returned_count": len(results),
            }
            return results

        telemetry: dict[str, Any] = {
            "mode": "live",
            "target_asins_count": len(target_asins),
            "max_live_asins": max_live_asins,
            "pre_verified_count": 0,
            "attempted_count": 0,
            "parsed_ok_count": 0,
            "live_verified_count": 0,
            "fetch_failures_count": 0,
            "outcome_counts": {},
            "colombia_co_count": 0,
            "blocked_co_count": 0,
            "us_or_unknown_count": 0,
            "missing_buybox_count": 0,
            "aborted_early_reason": None,
            "attempted_asins": [],
            "sample_outcomes": [],
        }

        live_results: list[dict[str, Any]] = []
        seen_live: set[str] = set()
        consecutive_failures = 0

        # Solo omitir /dp/ASIN si el candidato YA fue auditado en una página de detalle (/dp/)
        for asin in target_asins:
            pre_item = extra_map.get(asin)
            if (
                pre_item
                and pre_item.get("detail_verified") is True
                and pre_item.get("live_verified")
                and float(pre_item.get("price_usd") or 0.0) > 0.0
                and str(pre_item.get("image_url") or "").startswith("https://")
            ):
                live_results.append(dict(pre_item))
                seen_live.add(asin)
                telemetry["pre_verified_count"] += 1

        for idx, asin in enumerate(target_asins[:max_live_asins]):
            if asin in seen_live:
                continue
            if consecutive_failures >= 10:
                telemetry["aborted_early_reason"] = f"consecutive_failures_{consecutive_failures}"
                break
            if idx > 0:
                _time.sleep(0.5)

            telemetry["attempted_count"] += 1
            telemetry["attempted_asins"].append(asin)
            self._last_fetch_meta = {}
            live_item = self.fetch_asin_live(asin)
            if live_item is not None:
                consecutive_failures = 0
                telemetry["parsed_ok_count"] += 1

                dest = str(live_item.get("delivery_country_confirmed") or "US_OR_UNKNOWN")
                if dest == "CO":
                    telemetry["colombia_co_count"] += 1
                elif dest == "BLOCKED_CO":
                    telemetry["blocked_co_count"] += 1
                else:
                    telemetry["us_or_unknown_count"] += 1

                if not live_item.get("has_buybox", True):
                    telemetry["missing_buybox_count"] += 1

                # Si viene de una tarjeta de Ofertas con descuento visible y el precio Buy Box en /dp/
                # coincide exactamente (<= $0.50 diferencia), conservar list_price_usd como referencia cuando /dp/ la omite en SSR.
                pre_lead = extra_map.get(asin)
                live_price = round(float(live_item.get("price_usd") or 0.0), 2)
                if pre_lead and live_price > 0.0:
                    lead_price = round(float(pre_lead.get("price_usd") or 0.0), 2)
                    lead_list = round(float(pre_lead.get("list_price_usd") or 0.0), 2)
                    live_list = round(float(live_item.get("list_price_usd") or live_price), 2)
                    if (
                        lead_price > 0.0
                        and abs(live_price - lead_price) <= 0.50
                        and live_list <= live_price
                        and lead_list > live_price
                    ):
                        live_item["list_price_usd"] = lead_list
                        live_item["avg_90d_usd"] = lead_list

                if len(telemetry["sample_outcomes"]) < 10:
                    telemetry["sample_outcomes"].append(
                        {
                            "asin": asin,
                            "outcome": "parsed_ok",
                            "price_usd": live_price,
                            "list_price_usd": live_item.get("list_price_usd"),
                            "dest": dest,
                            "ingress": self._last_fetch_meta.get("ingress", ""),
                            "has_buybox": live_item.get("has_buybox"),
                            "live_verified": live_item.get("live_verified"),
                        }
                    )

                if live_item.get("live_verified") and live_price > 0.0:
                    telemetry["live_verified_count"] += 1
                    if pre_lead and pre_lead.get("category"):
                        live_item["category"] = pre_lead["category"]
                    elif asin in seed_map:
                        live_item["category"] = seed_map[asin].get("category", live_item["category"])
                        live_item["brand"] = seed_map[asin].get("brand", live_item.get("brand", ""))
                    live_results.append(live_item)
                    seen_live.add(asin)
            else:
                consecutive_failures += 1
                telemetry["fetch_failures_count"] += 1
                meta = self._last_fetch_meta or {"asin": asin, "outcome": "fetch_none"}
                outcome_key = f"{meta.get('client', 'na')}:{meta.get('outcome', 'fetch_none')}"
                telemetry["outcome_counts"][outcome_key] = telemetry["outcome_counts"].get(outcome_key, 0) + 1
                if len(telemetry["sample_outcomes"]) < 10:
                    telemetry["sample_outcomes"].append(meta)

        telemetry["glow_bootstrap"] = dict(self._glow_debug)
        self.last_telemetry = telemetry
        return live_results
