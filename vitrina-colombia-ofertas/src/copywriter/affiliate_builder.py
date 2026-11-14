"""Midas-Copy: Generador de enlaces canónicos de Amazon Associates y copywriting multicanal.

Transforma ofertas aprobadas para Colombia en:
- Enlaces limpios de afiliado (`?tag=pillepues-20&language=es_US`).
- Tarjetas HTML optimizadas para Telegram Bot API (`sendPhoto` <= 1024 caracteres).
- Tarjetas Adaptativas (Adaptive Cards v1.4) para Microsoft Teams Incoming Webhooks.
"""

from __future__ import annotations

import html
import re
from typing import Any

ASIN_DIRECT_RE = re.compile(r"^[A-Z0-9]{10}$", re.IGNORECASE)
ASIN_URL_RE = re.compile(
    r"(?:dp|gp/product|exec/obidos/asin)/([A-Z0-9]{10})(?:[/?&#]|$)",
    re.IGNORECASE,
)

LEGAL_DISCLAIMER = (
    "Enlace de afiliado de Amazon. El precio y disponibilidad pueden variar tras su publicación."
)


def extract_asin(url_or_asin: str) -> str:
    """Extrae y valida el ASIN de 10 caracteres desde un código directo o URL de Amazon.

    Args:
        url_or_asin: Cadena con un ASIN de 10 caracteres o una URL de producto de Amazon.

    Returns:
        El ASIN normalizado en mayúsculas (10 caracteres alfanuméricos).

    Raises:
        ValueError: Si no se encuentra un ASIN válido en la entrada.
    """
    if not url_or_asin or not isinstance(url_or_asin, str):
        raise ValueError("El ASIN o URL proporcionado no puede estar vacío.")

    candidate = url_or_asin.strip()
    if ASIN_DIRECT_RE.match(candidate):
        return candidate.upper()

    match = ASIN_URL_RE.search(candidate)
    if match:
        return match.group(1).upper()

    raise ValueError(f"No se pudo extraer un ASIN válido de: {url_or_asin!r}")


def build_affiliate_url(
    url_or_asin: str,
    associate_tag: str = "pillepues-20",
) -> str:
    """Construye el enlace canónico limpio de Amazon Associates eliminando parámetros basura.

    Args:
        url_or_asin: ASIN o URL de Amazon (con posibles parámetros ref, qid, sr, etc.).
        associate_tag: Tag de afiliado de Amazon Associates.

    Returns:
        URL canónica con formato `https://www.amazon.com/dp/{asin}?tag={associate_tag}&language=es_US`.
    """
    asin = extract_asin(url_or_asin)
    clean_tag = (associate_tag or "pillepues-20").strip()
    return f"https://www.amazon.com/dp/{asin}?tag={clean_tag}&language=es_US"


def build_vercel_deal_url(
    asin: str,
    public_web_url: str = "https://vitrina-colombia-ofertas.vercel.app",
) -> str:
    """Construye la URL directa a la ficha de la oferta en la web pública desplegada en Vercel.

    Args:
        asin: ASIN o URL del producto.
        public_web_url: URL base del portal web en Vercel.

    Returns:
        URL hacia la oferta en el catálogo web: `{public_web_url.rstrip('/')}/?asin={asin}`.
    """
    clean_asin = extract_asin(asin)
    base_url = (public_web_url or "https://vitrina-colombia-ofertas.vercel.app").strip().rstrip("/")
    return f"{base_url}/?asin={clean_asin}"


def _resolve_prices(deal: dict[str, Any]) -> tuple[float, float, float, int, str]:
    """Normaliza precios, ahorros, porcentaje de descuento y formato COP desde el dict de oferta."""
    price_usd = float(
        deal.get("price_usd", deal.get("current_price", deal.get("price", 0.0))) or 0.0
    )
    original_usd = float(
        deal.get(
            "original_price_usd",
            deal.get("list_price", deal.get("reference_price", deal.get("avg_90d", price_usd))),
        )
        or price_usd
    )
    if original_usd < price_usd:
        original_usd = price_usd

    savings_usd = float(deal.get("savings_usd", max(0.0, original_usd - price_usd)))
    raw_discount = deal.get("discount_pct", deal.get("discount_percent"))
    if raw_discount is None:
        discount_pct = int(round((savings_usd / original_usd) * 100)) if original_usd > 0 else 0
    else:
        discount_pct = int(round(float(raw_discount)))

    price_cop_formatted = str(deal.get("price_cop_formatted") or "").strip()
    if not price_cop_formatted:
        price_cop = deal.get("price_cop")
        if price_cop is None:
            trm = float(deal.get("trm_cop", 4150.0) or 4150.0)
            price_cop = round(price_usd * trm)
        price_cop_formatted = f"${int(round(float(price_cop))):,}".replace(",", ".") + " COP"
    elif "COP" not in price_cop_formatted.upper():
        price_cop_formatted = f"{price_cop_formatted} COP"

    return price_usd, original_usd, savings_usd, discount_pct, price_cop_formatted


def _resolve_colombia_badges(deal: dict[str, Any], price_usd: float) -> tuple[str, str, str]:
    """Obtiene los badges de impuestos DIAN, envío a Colombia y consejo de pago."""
    tax_badge_co = str(deal.get("tax_badge_co") or "").strip()
    if not tax_badge_co:
        if price_usd <= 200.0:
            tax_badge_co = "🟢 SIN IMPUESTOS DE IMPORTACIÓN (≤ $200 USD)"
        else:
            tax_badge_co = "🟡 PAGA IVA/ARANCEL EN AMAZON (> $200 USD)"

    shipping_badge_co = str(deal.get("shipping_badge_co") or "").strip()
    if not shipping_badge_co:
        if price_usd >= 35.0:
            shipping_badge_co = "✈️ Envío GRATIS a Colombia"
        else:
            shipping_badge_co = "📦 Envío GRATIS a Colombia completando $35 USD en carrito"

    colombia_tip = str(deal.get("colombia_tip") or "").strip()
    if not colombia_tip:
        colombia_tip = (
            "Paga en USD con tu tarjeta en Amazon para evitar recargos de conversión de moneda."
        )

    return tax_badge_co, shipping_badge_co, colombia_tip


def build_telegram_card(
    deal: dict[str, Any],
    associate_tag: str = "pillepues-20",
    public_web_url: str = "https://vitrina-colombia-ofertas.vercel.app",
) -> dict[str, Any]:
    """Genera el payload y copy HTML optimizado para `sendPhoto` de Telegram (máx 1024 caracteres).

    Args:
        deal: Diccionario con los datos de la oferta evaluada.
        associate_tag: Tag de afiliado de Amazon Associates.
        public_web_url: URL pública de la web en Vercel.

    Returns:
        Diccionario listo para enviar por Telegram Bot API con `caption_html` y `reply_markup`.
    """
    asin = extract_asin(str(deal.get("asin") or deal.get("url") or ""))
    affiliate_url = str(deal.get("affiliate_url") or "").strip() or build_affiliate_url(
        asin, associate_tag=associate_tag
    )
    vercel_deal_url = str(deal.get("web_url") or "").strip() or build_vercel_deal_url(
        asin, public_web_url=public_web_url
    )

    title_raw = str(deal.get("title") or f"Producto Amazon {asin}").strip()
    deal_tier_raw = str(deal.get("deal_tier") or "⚡ GRAN OFERTA").strip()

    price_usd, original_usd, savings_usd, discount_pct, price_cop_formatted = _resolve_prices(deal)
    tax_badge_co, shipping_badge_co, colombia_tip = _resolve_colombia_badges(deal, price_usd)

    highlights_raw = deal.get("highlights") or []
    if isinstance(highlights_raw, str):
        highlights_list = [highlights_raw]
    else:
        highlights_list = [str(item).strip() for item in highlights_raw if str(item).strip()]

    def _render_caption(title_text: str, max_highlights: int) -> str:
        safe_tier = html.escape(deal_tier_raw)
        safe_title = html.escape(title_text)
        safe_cop = html.escape(price_cop_formatted)
        safe_tax = html.escape(tax_badge_co)
        safe_ship = html.escape(shipping_badge_co)
        safe_tip = html.escape(colombia_tip)
        safe_disclaimer = html.escape(LEGAL_DISCLAIMER)

        lines: list[str] = [
            f"<b>[{safe_tier}] {safe_title} (-{discount_pct}% OFF)</b>",
            "",
            f"💵 <b>Precio Oferta:</b> ${price_usd:.2f} USD (<i>~{safe_cop}</i>)",
            f"❌ <b>Precio Normal:</b> <s>${original_usd:.2f} USD</s> (Ahorras ${savings_usd:.2f} USD)",
            "",
            f"🇨🇴 {safe_tax}",
            f"🚚 {safe_ship}",
        ]

        selected_highlights = highlights_list[:max_highlights]
        if selected_highlights:
            lines.append("")
            for bullet in selected_highlights:
                lines.append(f"• {html.escape(bullet)}")

        lines.extend(
            [
                "",
                f"💡 <b>Tip Colombia:</b> {safe_tip}",
                f"<i>ℹ️ {safe_disclaimer}</i>",
            ]
        )
        return "\n".join(lines)

    caption_html = _render_caption(title_raw, max_highlights=3)
    if len(caption_html) > 1024:
        caption_html = _render_caption(title_raw[:120] + "...", max_highlights=2)
    if len(caption_html) > 1024:
        caption_html = _render_caption(title_raw[:80] + "...", max_highlights=0)
    if len(caption_html) > 1024:
        caption_html = caption_html[:1020] + "..."

    reply_markup = {
        "inline_keyboard": [
            [
                {
                    "text": f"🛒 Comprar en Amazon.com (${price_usd:.2f} USD)",
                    "url": affiliate_url,
                }
            ],
            [
                {
                    "text": "🇨🇴 Ver Análisis y TRM en la Web",
                    "url": vercel_deal_url,
                }
            ],
        ]
    }

    return {
        "asin": asin,
        "title": title_raw,
        "photo_url": str(deal.get("image_url") or ""),
        "caption_html": caption_html,
        "parse_mode": "HTML",
        "reply_markup": reply_markup,
        "affiliate_url": affiliate_url,
        "web_url": vercel_deal_url,
    }


def build_teams_adaptive_card(
    deal: dict[str, Any],
    associate_tag: str = "pillepues-20",
    public_web_url: str = "https://vitrina-colombia-ofertas.vercel.app",
) -> dict[str, Any]:
    """Construye el payload JSON completo con AdaptiveCard v1.4 para Microsoft Teams Webhook.

    Args:
        deal: Diccionario con los datos de la oferta evaluada.
        associate_tag: Tag de afiliado de Amazon Associates.
        public_web_url: URL pública de la web en Vercel.

    Returns:
        Diccionario con estructura `{"type": "message", "attachments": [...]}` para Teams.
    """
    asin = extract_asin(str(deal.get("asin") or deal.get("url") or ""))
    affiliate_url = str(deal.get("affiliate_url") or "").strip() or build_affiliate_url(
        asin, associate_tag=associate_tag
    )
    vercel_deal_url = str(deal.get("web_url") or "").strip() or build_vercel_deal_url(
        asin, public_web_url=public_web_url
    )

    title_raw = str(deal.get("title") or f"Producto Amazon {asin}").strip()
    deal_tier_raw = str(deal.get("deal_tier") or "⚡ GRAN OFERTA").strip()
    image_url = str(deal.get("image_url") or "").strip()

    price_usd, original_usd, savings_usd, discount_pct, price_cop_formatted = _resolve_prices(deal)
    tax_badge_co, shipping_badge_co, colombia_tip = _resolve_colombia_badges(deal, price_usd)

    body: list[dict[str, Any]] = [
        {
            "type": "TextBlock",
            "text": f"🇨🇴 OFERTAS AMAZON COLOMBIA | {deal_tier_raw}",
            "weight": "Bolder",
            "color": "Accent",
            "size": "Small",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": f"{title_raw} (-{discount_pct}% OFF)",
            "weight": "Bolder",
            "size": "Large",
            "wrap": True,
        },
    ]

    if image_url:
        body.append(
            {
                "type": "Image",
                "url": image_url,
                "size": "Large",
                "altText": title_raw,
            }
        )

    body.extend(
        [
            {
                "type": "FactSet",
                "facts": [
                    {
                        "title": "Precio Oferta USD",
                        "value": f"${price_usd:.2f} USD",
                    },
                    {
                        "title": "Estimado en Pesos (COP)",
                        "value": price_cop_formatted,
                    },
                    {
                        "title": "Precio Normal",
                        "value": f"${original_usd:.2f} USD (Ahorras ${savings_usd:.2f} USD)",
                    },
                    {
                        "title": "Descuento Real",
                        "value": f"-{discount_pct}% OFF",
                    },
                    {
                        "title": "Aduana DIAN Colombia",
                        "value": tax_badge_co,
                    },
                    {
                        "title": "Envío a Colombia",
                        "value": shipping_badge_co,
                    },
                ],
            },
            {
                "type": "TextBlock",
                "text": f"💡 Tip Colombia: {colombia_tip}",
                "wrap": True,
                "spacing": "Medium",
                "size": "Small",
            },
            {
                "type": "TextBlock",
                "text": f"ℹ️ {LEGAL_DISCLAIMER}",
                "isSubtle": True,
                "wrap": True,
                "size": "Small",
                "spacing": "Small",
            },
        ]
    )

    adaptive_card_content: dict[str, Any] = {
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "type": "AdaptiveCard",
        "version": "1.4",
        "body": body,
        "actions": [
            {
                "type": "Action.OpenUrl",
                "title": f"🛒 Comprar en Amazon.com (${price_usd:.2f} USD)",
                "url": affiliate_url,
            },
            {
                "type": "Action.OpenUrl",
                "title": "🇨🇴 Ver Análisis y TRM en la Web",
                "url": vercel_deal_url,
            },
        ],
    }

    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "contentUrl": None,
                "content": adaptive_card_content,
            }
        ],
    }
