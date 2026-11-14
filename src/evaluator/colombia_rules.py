"""Evaluador cuantitativo de ofertas de Amazon.com para compradores en Colombia (Arancel-Guardian).

Valida:
1. Exención de arancel e IVA de importación en Colombia (DIAN: <= $200 USD).
2. Elegibilidad de Envío Gratis a Colombia (AmazonGlobal >= $35 USD).
3. Conversión estimada a Pesos Colombianos (COP) según TRM del día.
4. Descuento real frente al mínimo entre precio promedio de 90 días y precio de lista.
"""

from __future__ import annotations

import json
import urllib.request
from typing import Any


def format_cop(amount_cop: int | float) -> str:
    """Formatea un monto numérico en pesos colombianos con puntos de miles (ej. '$497.958 COP')."""
    rounded = int(round(float(amount_cop)))
    formatted = f"{rounded:,}".replace(",", ".")
    return f"${formatted} COP"


def fetch_live_trm_cop(default_trm: float = 4150.0) -> float:
    """Obtiene la TRM oficial de Colombia desde datos.gov.co con fallback seguro."""
    url = "https://www.datos.gov.co/resource/32sa-8pi3.json?$limit=1&$order=vigenciadesde%20DESC"
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "AmazonColombiaAffiliates-ArancelGuardian/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=2.5) as response:
            if response.status == 200:
                payload = json.loads(response.read().decode("utf-8"))
                if isinstance(payload, list) and payload:
                    raw_val = payload[0].get("valor")
                    if raw_val is not None:
                        trm = float(raw_val)
                        if trm > 1000.0:
                            return round(trm, 2)
    except Exception:
        pass
    return float(default_trm)


def _compute_reference_price(price_usd: float, avg_90d_usd: float, list_price_usd: float) -> float:
    """Determina el precio de referencia honesto entre avg_90d_usd y list_price_usd."""
    candidates = [val for val in (avg_90d_usd, list_price_usd) if val and val > 0.0]
    if len(candidates) == 2:
        return min(candidates)
    if len(candidates) == 1:
        return candidates[0]
    return price_usd


def evaluate_colombia_deal(
    product: dict[str, Any],
    trm_cop: float = 4150.0,
    tax_free_limit_usd: float = 200.0,
    free_shipping_min_usd: float = 35.0,
    min_discount_pct: float = 20.0,
    allow_locker_deals: bool = False,
) -> dict[str, Any]:
    """Evalúa una oferta de Amazon.com según las reglas aduaneras y logísticas de Colombia.

    Retorna una copia enriquecida del diccionario `product`.
    """
    enriched = dict(product)

    price_usd = round(float(product.get("price_usd", 0.0) or 0.0), 2)
    list_price_usd = round(float(product.get("list_price_usd", 0.0) or 0.0), 2)
    avg_90d_usd = round(float(product.get("avg_90d_usd", 0.0) or 0.0), 2)
    ships_to_colombia = bool(product.get("ships_to_colombia", True))
    requires_locker = bool(product.get("requires_locker", not ships_to_colombia)) or not ships_to_colombia
    free_shipping_co = bool(product.get("free_shipping_co", False)) and not requires_locker

    reference_price = round(_compute_reference_price(price_usd, avg_90d_usd, list_price_usd), 2)

    if reference_price > 0.0 and reference_price > price_usd:
        discount_pct = round(((reference_price - price_usd) / reference_price) * 100.0, 1)
    else:
        discount_pct = 0.0

    # Comparación explícita vs promedio histórico de 90 días
    cheaper_than_before = bool(avg_90d_usd > price_usd)
    if avg_90d_usd > 0.0 and avg_90d_usd > price_usd:
        vs_avg_90d_pct = round(((avg_90d_usd - price_usd) / avg_90d_usd) * 100.0, 1)
        price_vs_90d_badge = (
            f"📉 {vs_avg_90d_pct:.1f}% más barato que su promedio de 90 días (${avg_90d_usd:.2f} USD)"
        )
    else:
        vs_avg_90d_pct = 0.0
        price_vs_90d_badge = f"➡️ Precio dentro del rango de 90 días (${avg_90d_usd:.2f} USD)"

    # Costo de envío y requerimiento de casillero
    if not requires_locker and free_shipping_co and price_usd >= free_shipping_min_usd:
        shipping_cost_usd = 0.0
    elif "shipping_cost_usd" in product and product["shipping_cost_usd"] is not None:
        shipping_cost_usd = round(float(product["shipping_cost_usd"]), 2)
    else:
        shipping_cost_usd = 8.50 if requires_locker else 11.95

    shipping_cost_cop = int(round(shipping_cost_usd * trm_cop))
    shipping_cost_formatted = (
        "GRATIS ($0 USD)"
        if (not requires_locker and shipping_cost_usd == 0.0)
        else f"+${shipping_cost_usd:.2f} USD (~{format_cop(shipping_cost_cop)})"
    )

    locker_badge_co = (
        "📦 Necesita casillero: Sí (Casillero en Miami)"
        if requires_locker
        else "✅ Necesita casillero: No (Envío directo a Colombia)"
    )

    # 1. Regla aduanera DIAN de Colombia (exención <= $200 USD)
    tax_free_colombia = price_usd <= tax_free_limit_usd
    estimated_import_tax_usd = 0.0 if tax_free_colombia else round(price_usd * 0.19, 2)
    total_landed_usd = round(price_usd + shipping_cost_usd + estimated_import_tax_usd, 2)

    # 2. Valores en Pesos Colombianos (COP)
    price_cop = int(round(price_usd * trm_cop))
    total_landed_cop = int(round(total_landed_usd * trm_cop))
    savings_usd = round(max(0.0, reference_price - price_usd), 2)
    savings_cop = int(round(savings_usd * trm_cop))

    # 3. Insignias de impuestos y envío para Colombia
    tax_badge_co = (
        "🟢 Sin Impuestos DIAN (≤ $200 USD)"
        if tax_free_colombia
        else "⚠️ Paga IVA Importación (> $200 USD)"
    )

    if not requires_locker and shipping_cost_usd == 0.0:
        shipping_badge_co = "🇨🇴 Envío GRATIS directo a Colombia ($0)"
    elif not requires_locker:
        shipping_badge_co = f"✈️ Envío directo a Colombia: +${shipping_cost_usd:.2f} USD (Gratis desde $35)"
    else:
        shipping_badge_co = f"📦 Sin envío directo — Envío vía casillero Miami: ~${shipping_cost_usd:.2f} USD"

    # 4. Clasificación de la oferta (Envío a Colombia obligatorio salvo allow_locker_deals + Anti-Humo)
    ships_direct_to_colombia = bool(ships_to_colombia and not requires_locker)
    valid_discount = bool(
        price_usd > 0.0
        and reference_price > price_usd
        and savings_usd >= 1.0
        and discount_pct >= min_discount_pct
        and cheaper_than_before
    )
    if not ships_direct_to_colombia:
        if allow_locker_deals and valid_discount:
            deal_tier = "📦 VÍA CASILLERO MIAMI"
        else:
            deal_tier = "❌ SIN ENVÍO A COLOMBIA"
    elif valid_discount and discount_pct >= 35.0:
        deal_tier = "🔥 MÍNIMO HISTÓRICO"
    elif valid_discount:
        deal_tier = "⚡ GRAN OFERTA"
    else:
        deal_tier = "❌ DESCARTAR"

    approved_for_colombia = bool(
        (ships_direct_to_colombia or allow_locker_deals)
        and valid_discount
    )

    # 5. Consejo práctico para compradores en Colombia
    if requires_locker:
        colombia_tip = (
            "Este producto NO tiene envío directo de Amazon a Colombia; requiere casillero en Miami "
            f"(~${shipping_cost_usd:.2f} USD de flete) y paga siempre en USD."
        )
    elif tax_free_colombia and shipping_cost_usd == 0.0:
        colombia_tip = (
            "Paga en USD con tu tarjeta en Amazon para evitar el recargo del conversor de moneda "
            "y aprovecha envío GRATIS directo a Colombia sin casillero y $0 de arancel/IVA (≤ $200 USD)."
        )
    elif tax_free_colombia:
        missing_for_free_ship = round(max(0.0, free_shipping_min_usd - price_usd), 2)
        colombia_tip = (
            f"Envío directo sin casillero (+${shipping_cost_usd:.2f} USD). Agrega ${missing_for_free_ship:.2f} USD "
            "más en productos elegibles para desbloquear Envío GRATIS a Colombia."
        )
    else:
        colombia_tip = (
            "Supera el tope de $200 USD de la DIAN (aplica ~19% de IVA de importación). "
            "Paga en USD en el checkout de Amazon para ahorrar en la tasa de cambio."
        )

    enriched.update(
        {
            "price_usd": price_usd,
            "list_price_usd": list_price_usd,
            "avg_90d_usd": avg_90d_usd,
            "reference_price_usd": reference_price,
            "discount_pct": discount_pct,
            "cheaper_than_before": cheaper_than_before,
            "vs_avg_90d_pct": vs_avg_90d_pct,
            "price_vs_90d_badge": price_vs_90d_badge,
            "trm_cop": round(float(trm_cop), 2),
            "tax_free_colombia": tax_free_colombia,
            "estimated_import_tax_usd": estimated_import_tax_usd,
            "free_shipping_co": free_shipping_co,
            "shipping_cost_usd": shipping_cost_usd,
            "shipping_cost_cop": shipping_cost_cop,
            "shipping_cost_formatted": shipping_cost_formatted,
            "ships_to_colombia": ships_direct_to_colombia,
            "requires_locker": requires_locker,
            "locker_badge_co": locker_badge_co,
            "total_landed_usd": total_landed_usd,
            "price_cop": price_cop,
            "price_cop_formatted": format_cop(price_cop),
            "total_landed_cop": total_landed_cop,
            "total_landed_cop_formatted": format_cop(total_landed_cop),
            "savings_usd": savings_usd,
            "savings_cop": savings_cop,
            "savings_cop_formatted": format_cop(savings_cop),
            "tax_badge_co": tax_badge_co,
            "shipping_badge_co": shipping_badge_co,
            "deal_tier": deal_tier,
            "approved_for_colombia": approved_for_colombia,
            "colombia_tip": colombia_tip,
        }
    )

    return enriched


def deal_priority_key(deal: dict[str, Any]) -> tuple[int, float, int, int, float]:
    """Ordena las ofertas aprobadas priorizando el mayor descuento real y beneficio para Colombia."""
    return (
        1 if deal.get("is_new_price_drop") else 0,
        float(deal.get("discount_pct") or 0.0),
        1 if deal.get("free_shipping_co") else 0,
        1 if deal.get("tax_free_colombia") else 0,
        float(deal.get("savings_usd") or 0.0),
    )
