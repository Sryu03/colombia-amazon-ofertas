"""Midas-Copy: Generador de enlaces canónicos de Amazon Associates y copywriting para Telegram y Web.

Transforma ofertas aprobadas para Colombia en:
- Enlaces limpios de afiliado estilo SiteStripe (`?linkCode=ll1&tag=pillepues-20&language=es_US&ref_=as_li_ss_tl`).
- Tarjetas HTML optimizadas para Telegram Bot API (`sendPhoto` <= 1024 caracteres).
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
    """Extrae y valida el ASIN de 10 caracteres desde un código directo o URL de Amazon."""
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
    """Construye el enlace canónico de Amazon Associates con parámetros estándar de SiteStripe."""
    asin = extract_asin(url_or_asin)
    clean_tag = (associate_tag or "pillepues-20").strip()
    return (
        f"https://www.amazon.com/dp/{asin}"
        f"?linkCode=ll1&tag={clean_tag}&language=es_US&ref_=as_li_ss_tl"
    )


def build_vercel_deal_url(
    asin: str,
    public_web_url: str = "https://vitrina-colombia-ofertas.vercel.app",
) -> str:
    """Construye la URL directa a la ficha de la oferta en la web pública desplegada en Vercel."""
    clean_asin = extract_asin(asin)
    base_url = (public_web_url or "https://vitrina-colombia-ofertas.vercel.app").strip().rstrip("/")
    return f"{base_url}/?asin={clean_asin}"


def _resolve_prices(deal: dict[str, Any]) -> tuple[float, float, float, float, int, str]:
    """Normaliza precios, promedio 90d, ahorros, % de descuento y formato COP con coherencia estricta."""
    price_usd = round(
        float(deal.get("price_usd", deal.get("current_price", deal.get("price", 0.0))) or 0.0),
        2,
    )
    avg_90d_usd = round(
        float(
            deal.get("avg_90d_usd", deal.get("avg_90d", deal.get("reference_price_usd", price_usd)))
            or price_usd
        ),
        2,
    )
    list_price_usd = round(
        float(
            deal.get("list_price_usd", deal.get("original_price_usd", avg_90d_usd))
            or avg_90d_usd
        ),
        2,
    )
    reference_usd = round(float(deal.get("reference_price_usd") or 0.0), 2)
    if reference_usd <= 0.0:
        candidates = [v for v in (avg_90d_usd, list_price_usd) if v > 0.0]
        reference_usd = min(candidates) if candidates else price_usd
    if reference_usd < price_usd:
        reference_usd = price_usd

    savings_usd = round(max(0.0, reference_usd - price_usd), 2)
    raw_discount = deal.get("discount_pct", deal.get("discount_percent"))
    if raw_discount is None or (reference_usd > price_usd and float(raw_discount) <= 0):
        discount_pct = int(round((savings_usd / reference_usd) * 100)) if reference_usd > 0 else 0
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

    return price_usd, reference_usd, avg_90d_usd, savings_usd, discount_pct, price_cop_formatted


def _resolve_colombia_badges(deal: dict[str, Any], price_usd: float) -> tuple[str, str, str, str]:
    """Obtiene los badges de impuestos DIAN, envío, casillero y consejo de pago."""
    tax_badge_co = str(deal.get("tax_badge_co") or "").strip()
    if not tax_badge_co:
        if price_usd <= 200.0:
            tax_badge_co = "🟢 Sin Impuestos DIAN (≤ $200 USD)"
        else:
            tax_badge_co = "⚠️ Paga IVA Importación (> $200 USD)"

    shipping_badge_co = str(deal.get("shipping_badge_co") or "").strip()
    if not shipping_badge_co:
        shipping_cost = float(deal.get("shipping_cost_usd", 0.0) or 0.0)
        if shipping_cost == 0.0 and price_usd >= 35.0:
            shipping_badge_co = "🇨🇴 Envío GRATIS directo a Colombia ($0)"
        else:
            shipping_badge_co = f"✈️ Envío a Colombia: +${shipping_cost:.2f} USD"

    locker_badge_co = str(deal.get("locker_badge_co") or "").strip()
    if not locker_badge_co:
        requires_locker = bool(deal.get("requires_locker", False))
        locker_badge_co = (
            "📦 Necesita casillero: Sí (Casillero en Miami)"
            if requires_locker
            else "✅ Necesita casillero: No (Envío directo a Colombia)"
        )

    colombia_tip = str(deal.get("colombia_tip") or "").strip()
    if not colombia_tip:
        colombia_tip = (
            "Paga en USD con tu tarjeta en Amazon para evitar recargos de conversión de moneda."
        )

    return tax_badge_co, shipping_badge_co, locker_badge_co, colombia_tip


def build_telegram_card(
    deal: dict[str, Any],
    associate_tag: str = "pillepues-20",
    public_web_url: str = "https://vitrina-colombia-ofertas.vercel.app",
) -> dict[str, Any]:
    """Genera el payload y copy HTML optimizado para `sendPhoto` de Telegram (máx 1024 caracteres)."""
    asin = extract_asin(str(deal.get("asin") or deal.get("url") or ""))
    raw_aff_url = str(deal.get("affiliate_url") or "").strip()
    affiliate_url = (
        raw_aff_url
        if (raw_aff_url and "linkCode=" in raw_aff_url and "tag=" in raw_aff_url)
        else build_affiliate_url(asin, associate_tag=associate_tag)
    )
    vercel_deal_url = str(deal.get("web_url") or "").strip() or build_vercel_deal_url(
        asin, public_web_url=public_web_url
    )

    title_raw = str(deal.get("title") or f"Producto Amazon {asin}").strip()
    deal_tier_raw = str(deal.get("deal_tier") or "⚡ GRAN OFERTA").strip()

    price_usd, reference_usd, avg_90d_usd, savings_usd, discount_pct, price_cop_formatted = (
        _resolve_prices(deal)
    )
    tax_badge_co, shipping_badge_co, locker_badge_co, colombia_tip = _resolve_colombia_badges(
        deal, price_usd
    )
    trm_cop = float(deal.get("trm_cop", 4150.0) or 4150.0)
    cheaper_than_before = bool(deal.get("cheaper_than_before", avg_90d_usd > price_usd))

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
        safe_locker = html.escape(locker_badge_co)
        safe_tip = html.escape(colombia_tip)
        safe_disclaimer = html.escape(LEGAL_DISCLAIMER)

        strike_ref = reference_usd if reference_usd > price_usd else avg_90d_usd
        hist_line = (
            f"📉 <b>Más barato que antes:</b> Antes <s>${strike_ref:.2f} USD</s> → Hoy <b>-{discount_pct}% OFF</b>"
            if cheaper_than_before and strike_ref > price_usd
            else f"🏷️ <b>Descuento:</b> -{discount_pct}% OFF (Antes <s>${strike_ref:.2f} USD</s>)"
        )

        lines: list[str] = [
            f"🔥 <b>PillePues · [{safe_tier}] (-{discount_pct}% OFF)</b>",
            f"📦 <b>{safe_title}</b>",
            "",
            f"💵 <b>Precio Hoy:</b> <b>${price_usd:.2f} USD</b> (<i>~{safe_cop}</i> · TRM ${int(round(trm_cop)):,})".replace(",", "."),
            f"{hist_line} · <b>Ahorras ${savings_usd:.2f} USD</b>",
            "",
            f"🚚 <b>Envío:</b> {safe_ship}",
            f"📬 {safe_locker}",
            f"🇨🇴 {safe_tax}",
        ]

        selected_highlights = highlights_list[:max_highlights]
        if selected_highlights:
            lines.append("")
            for bullet in selected_highlights:
                lines.append(f"• {html.escape(bullet)}")

        lines.extend(
            [
                "",
                f"💡 <b>Tip PillePues:</b> {safe_tip}",
                f"📣 <b>Canal oficial:</b> @pillepues · <i>ℹ️ {safe_disclaimer}</i>",
            ]
        )
        return "\n".join(lines)

    caption_html = _render_caption(title_raw, max_highlights=2)
    if len(caption_html) > 1024:
        caption_html = _render_caption(title_raw[:110] + "...", max_highlights=1)
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
                    "text": "🇨🇴 Ver Análisis y TRM en PillePues",
                    "url": vercel_deal_url,
                }
            ],
        ]
    }

    from src.broadcaster.card_image import upgrade_amazon_image_url

    hd_photo_url = upgrade_amazon_image_url(str(deal.get("image_url") or ""), size=1200)
    deal_snapshot = {
        "asin": asin,
        "title": title_raw,
        "price_usd": price_usd,
        "reference_price_usd": reference_usd,
        "discount_pct": discount_pct,
        "price_cop": deal.get("price_cop"),
        "trm_cop": trm_cop,
        "ships_to_colombia": bool(deal.get("ships_to_colombia", False)),
        "free_shipping_co": bool(deal.get("free_shipping_co", False)),
        "requires_locker": bool(deal.get("requires_locker", False)),
        "tax_free_colombia": bool(deal.get("tax_free_colombia", price_usd <= 200.0)),
    }

    return {
        "asin": asin,
        "title": title_raw,
        "photo_url": hd_photo_url,
        "caption_html": caption_html,
        "parse_mode": "HTML",
        "reply_markup": reply_markup,
        "affiliate_url": affiliate_url,
        "web_url": vercel_deal_url,
        "deal_snapshot": deal_snapshot,
    }
