from __future__ import annotations

from typing import Any


def detect_price_drop(
    current_price: float,
    avg_90d: float,
    list_price: float,
    min_discount_pct: float = 20.0,
) -> dict[str, Any]:
    """
    Deterministic Zero-Token price drop detector against real 90-day historical mean
    and list price to prevent inflated list price ('anti-humo') false discounts.
    """
    current_price = float(current_price)
    avg_90d = float(avg_90d)
    list_price = float(list_price)
    min_discount_pct = float(min_discount_pct)

    reference_price = (
        min(avg_90d, list_price)
        if (avg_90d > 0 and list_price > 0)
        else max(avg_90d, list_price)
    )

    if reference_price <= 0 or current_price <= 0 or current_price >= reference_price:
        return {
            "is_deal": False,
            "discount_pct": 0.0,
            "savings_usd": 0.0,
            "reference_price": round(reference_price, 2) if reference_price > 0 else reference_price,
            "is_historic_low": False,
        }

    discount_pct = round(((reference_price - current_price) / reference_price) * 100, 1)
    savings_usd = round(reference_price - current_price, 2)
    is_historic_low = discount_pct >= 35.0
    is_deal = discount_pct >= min_discount_pct

    return {
        "is_deal": is_deal,
        "discount_pct": discount_pct,
        "savings_usd": savings_usd,
        "reference_price": round(reference_price, 2),
        "is_historic_low": is_historic_low,
    }
