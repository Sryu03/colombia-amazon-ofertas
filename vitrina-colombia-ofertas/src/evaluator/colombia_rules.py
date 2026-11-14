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
) -> dict[str, Any]:
    """Evalúa una oferta de Amazon.com según las reglas aduaneras y logísticas de Colombia.

    Retorna una copia enriquecida del diccionario `product`.
    """
    enriched = dict(product)

    price_usd = round(float(product.get("price_usd", 0.0) or 0.0), 2)
    list_price_usd = round(float(product.get("list_price_usd", 0.0) or 0.0), 2)
    avg_90d_usd = round(float(product.get("avg_90d_usd", 0.0) or 0.0), 2)
    ships_to_colombia = bool(product.get("ships_to_colombia", True))
    free_shipping_co = bool(product.get("free_shipping_co", False))

    reference_price = round(_compute_reference_price(price_usd, avg_90d_usd, list_price_usd), 2)

    if reference_price > 0.0 and reference_price > price_usd:
        discount_pct = round(((reference_price - price_usd) / reference_price) * 100.0, 1)
    else:
        discount_pct = 0.0

    # 1. Regla aduanera DIAN de Colombia (exención <= $200 USD)
    tax_free_colombia = price_usd <= tax_free_limit_usd
    estimated_import_tax_usd = 0.0 if tax_free_colombia else round(price_usd * 0.19, 2)
    total_landed_usd = round(price_usd + estimated_import_tax_usd, 2)

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

    if free_shipping_co and price_usd >= free_shipping_min_usd:
        shipping_badge_co = "🇨🇴 Envío GRATIS directo a Colombia"
    elif free_shipping_co and price_usd < free_shipping_min_usd:
        shipping_badge_co = "📦 Envío GRATIS a CO completando $35 USD"
    else:
        shipping_badge_co = "✈️ Envío Internacional / Casillero"

    # 4. Clasificación de la oferta (Anti-Humo)
    if discount_pct >= 35.0:
        deal_tier = "🔥 MÍNIMO HISTÓRICO"
    elif discount_pct >= min_discount_pct:
        deal_tier = "⚡ GRAN OFERTA"
    else:
        deal_tier = "❌ DESCARTAR"

    approved_for_colombia = bool(ships_to_colombia and discount_pct >= min_discount_pct)

    # 5. Consejo práctico para compradores en Colombia
    if tax_free_colombia and free_shipping_co and price_usd >= free_shipping_min_usd:
        colombia_tip = (
            "Paga en USD con tu tarjeta en Amazon para evitar el recargo del conversor de moneda "
            "y aprovecha envío GRATIS directo a Colombia con $0 de arancel/IVA (≤ $200 USD)."
        )
    elif tax_free_colombia and free_shipping_co and price_usd < free_shipping_min_usd:
        missing_for_free_ship = round(max(0.0, free_shipping_min_usd - price_usd), 2)
        colombia_tip = (
            f"Agrega ${missing_for_free_ship:.2f} USD más en productos elegibles para desbloquear "
            "Envío GRATIS a Colombia sin impuestos DIAN y paga siempre en USD."
        )
    elif tax_free_colombia:
        colombia_tip = (
            "Exento de IVA y arancel DIAN (≤ $200 USD). Recuerda pagar en USD en Amazon para "
            "obtener la TRM real de tu banco sin comisión oculta de conversión."
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
            "trm_cop": round(float(trm_cop), 2),
            "tax_free_colombia": tax_free_colombia,
            "estimated_import_tax_usd": estimated_import_tax_usd,
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
