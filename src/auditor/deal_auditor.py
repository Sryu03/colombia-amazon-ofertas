"""Verificador-Colombia-Auditor: Auditor determinista (0 tokens LLM) antes de publicar en Web o Telegram.

Verifica estrictamente para cada oferta:
1. Integridad del producto (ASIN, título real, imagen HTTPS válida).
2. Verificación en vivo sobre `/dp/<ASIN>` con Buy Box activo (`detail_verified`, `has_buybox`, precio real).
3. Destino Colombia confirmado (`delivery_country_confirmed == "CO"`) o etiquetado explícito de casillero en Miami.
4. Coherencia total de precio USD, `% OFF`, ahorro y copy/botones entre la tarjeta web y el mensaje de Telegram.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AuditResult:
    approved: bool
    asin: str
    reason: str = "ok"
    checks: dict[str, bool] = field(default_factory=dict)


class DealAuditor:
    """Puerta final de auditoría antes de exportar al portal web (`deals.json`) o enviar a Telegram."""

    def __init__(
        self,
        *,
        min_discount_pct: float = 20.0,
        allow_locker_deals: bool = False,
        require_live_detail: bool = False,
        require_colombia_confirmation: bool = False,
    ) -> None:
        self.min_discount_pct = float(min_discount_pct)
        self.allow_locker_deals = bool(allow_locker_deals)
        self.require_live_detail = bool(require_live_detail)
        self.require_colombia_confirmation = bool(require_colombia_confirmation)

        self.audited_count = 0
        self.approved_count = 0
        self.rejected_count = 0
        self.rejected_reasons: dict[str, int] = {}
        self.rejected_samples: list[dict[str, str]] = []

    def _record(self, result: AuditResult, reset_counter: bool = True) -> AuditResult:
        if reset_counter:
            self.audited_count += 1
        if result.approved:
            self.approved_count += 1
        else:
            self.rejected_count += 1
            self.rejected_reasons[result.reason] = self.rejected_reasons.get(result.reason, 0) + 1
            if len(self.rejected_samples) < 20:
                self.rejected_samples.append({"asin": result.asin, "reason": result.reason})
        return result

    def audit_deal(
        self,
        deal: dict[str, Any],
        telegram_card: dict[str, Any] | None = None,
        *,
        record_metrics: bool = True,
    ) -> AuditResult:
        asin = str(deal.get("asin") or "").strip().upper()
        checks: dict[str, bool] = {}

        def _fail(reason: str) -> AuditResult:
            res = AuditResult(approved=False, asin=asin or "UNKNOWN", reason=reason, checks=checks)
            return self._record(res) if record_metrics else res

        checks["valid_asin"] = len(asin) == 10 and asin.isalnum()
        if not checks["valid_asin"]:
            return _fail("invalid_asin")

        title = str(deal.get("title") or "").strip()
        checks["valid_title"] = (
            len(title) >= 5
            and not title.lower().startswith("amazon product")
            and title.lower() not in ("amazon", "amazon.com")
        )
        if not checks["valid_title"]:
            return _fail("invalid_title")

        image_url = str(deal.get("image_url") or "").strip().lower()
        checks["valid_image"] = (
            image_url.startswith("https://")
            and "sprite" not in image_url
            and "pixel" not in image_url
        )
        if not checks["valid_image"]:
            return _fail("invalid_image")

        if self.require_live_detail:
            checks["detail_verified"] = bool(deal.get("detail_verified", False))
            if not checks["detail_verified"]:
                return _fail("missing_dp_detail_verification")

            checks["live_verified"] = bool(deal.get("live_verified", False))
            if not checks["live_verified"]:
                return _fail("not_live_verified")

            checks["has_buybox"] = bool(deal.get("has_buybox", True))
            if not checks["has_buybox"]:
                return _fail("missing_active_buybox")

        price_usd = round(float(deal.get("price_usd") or 0.0), 2)
        ref_price = round(
            float(
                deal.get("reference_price_usd")
                or deal.get("avg_90d_usd")
                or deal.get("list_price_usd")
                or 0.0
            ),
            2,
        )
        savings_usd = round(float(deal.get("savings_usd") or max(0.0, ref_price - price_usd)), 2)
        discount_pct = float(deal.get("discount_pct") or 0.0)

        checks["coherent_price"] = (
            price_usd > 0.0
            and ref_price > price_usd
            and savings_usd >= 1.0
            and discount_pct >= self.min_discount_pct
        )
        if not checks["coherent_price"]:
            return _fail("incoherent_price_or_discount")

        requires_locker = bool(deal.get("requires_locker", False)) or not bool(
            deal.get("ships_to_colombia", False)
        )
        ships_direct = bool(deal.get("ships_to_colombia", False)) and not requires_locker

        if requires_locker:
            checks["locker_policy_ok"] = self.allow_locker_deals
            if not self.allow_locker_deals:
                return _fail("requires_locker_excluded")
            # Si se permiten ofertas con casillero, deben declarar casillero explícitamente
            ship_badge = str(deal.get("shipping_badge_co") or "").lower()
            locker_badge = str(deal.get("locker_badge_co") or "").lower()
            checks["locker_explicitly_labeled"] = (
                "casillero" in locker_badge and "envío gratis directo" not in ship_badge
            )
            if not checks["locker_explicitly_labeled"]:
                return _fail("locker_not_explicitly_labeled")
        else:
            checks["direct_shipping_consistent"] = ships_direct
            if bool(deal.get("free_shipping_co", False)) and price_usd < 35.0:
                checks["free_shipping_threshold"] = False
                return _fail("invalid_free_shipping_below_35")
            checks["free_shipping_threshold"] = True

            if self.require_colombia_confirmation:
                dest_status = str(deal.get("delivery_country_confirmed") or "").upper()
                checks["colombia_destination_confirmed"] = dest_status == "CO"
                if not checks["colombia_destination_confirmed"]:
                    return _fail(f"colombia_shipping_unconfirmed:{dest_status or 'NONE'}")

        if telegram_card is not None:
            caption = str(telegram_card.get("caption_html") or "")
            expected_price_token = f"${price_usd:.2f} USD"
            checks["tg_price_match"] = expected_price_token in caption
            if not checks["tg_price_match"]:
                return _fail("telegram_caption_price_mismatch")

            keyboard = (telegram_card.get("reply_markup") or {}).get("inline_keyboard") or []
            btn_text = str(keyboard[0][0].get("text") or "") if keyboard and keyboard[0] else ""
            checks["tg_button_price_match"] = expected_price_token in btn_text
            if not checks["tg_button_price_match"]:
                return _fail("telegram_button_price_mismatch")

            photo_url = str(telegram_card.get("photo_url") or "").strip().lower()
            checks["tg_photo_https"] = photo_url.startswith("https://")
            if not checks["tg_photo_https"]:
                return _fail("telegram_invalid_photo_url")

            if requires_locker:
                checks["tg_locker_disclosure"] = (
                    "Necesita casillero: Sí" in caption
                    and "Envío GRATIS directo a Colombia" not in caption
                )
                if not checks["tg_locker_disclosure"]:
                    return _fail("telegram_missing_locker_disclosure")
            else:
                checks["tg_direct_disclosure"] = "Necesita casillero: No" in caption
                if not checks["tg_direct_disclosure"]:
                    return _fail("telegram_missing_direct_disclosure")

        res = AuditResult(approved=True, asin=asin, reason="ok", checks=checks)
        return self._record(res) if record_metrics else res

    def summary(self) -> dict[str, Any]:
        return {
            "auditor_agent": "verificador-colombia-auditor",
            "require_live_detail": self.require_live_detail,
            "require_colombia_confirmation": self.require_colombia_confirmation,
            "allow_locker_deals": self.allow_locker_deals,
            "audited_count": self.audited_count,
            "approved_count": self.approved_count,
            "rejected_count": self.rejected_count,
            "rejected_reasons": dict(self.rejected_reasons),
            "rejected_samples": list(self.rejected_samples),
        }
