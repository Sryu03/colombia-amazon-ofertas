"""Historial persistente de precios en JSON para detectar bajadas reales entre ejecuciones en la nube."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class PriceHistoryStore:
    """
    Almacena el último precio visto, mínimo histórico observado y último precio publicado
    en Telegram por cada ASIN. Permite publicar al instante apenas baja un precio
    sin repetir ofertas ya enviadas al mismo valor.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.records: dict[str, dict[str, Any]] = {}
        self.load()

    def load(self) -> None:
        if self.path.exists():
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    self.records = raw
                    return
            except Exception:
                pass
        self.records = {}

    def save(self) -> str:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self.records, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return str(self.path)

    def get_baseline_avg(self, asin: str) -> float | None:
        """Devuelve el promedio histórico observado previamente para el ASIN si existe."""
        prev = self.records.get(asin.upper())
        if not prev:
            return None
        val = prev.get("avg_90d_usd") or prev.get("last_price_usd")
        try:
            fval = float(val)
            return fval if fval > 0 else None
        except (TypeError, ValueError):
            return None

    def evaluate_and_record(
        self,
        asin: str,
        current_price_usd: float,
        avg_90d_usd: float,
        min_drop_delta_usd: float = 1.0,
    ) -> dict[str, Any]:
        """
        Registra el precio actual y determina si representa una bajada nueva respecto al
        último precio publicado en Telegram.
        """
        asin_key = asin.upper()
        now_iso = datetime.now(timezone.utc).isoformat()
        prev = self.records.get(asin_key)

        if not prev:
            self.records[asin_key] = {
                "asin": asin_key,
                "last_price_usd": round(current_price_usd, 2),
                "min_price_seen_usd": round(current_price_usd, 2),
                "avg_90d_usd": round(avg_90d_usd, 2),
                "last_published_price_usd": None,
                "first_seen_at": now_iso,
                "last_seen_at": now_iso,
                "last_published_at": None,
            }
            return {
                "is_new_drop": True,
                "previous_price_usd": None,
                "price_delta_usd": 0.0,
                "is_all_time_low_seen": True,
            }

        prev_price = float(prev.get("last_price_usd") or current_price_usd)
        min_seen = min(float(prev.get("min_price_seen_usd") or current_price_usd), current_price_usd)
        last_pub = prev.get("last_published_price_usd")

        # Promedio móvil simple para ir afinando el promedio histórico real
        prev_avg = float(prev.get("avg_90d_usd") or avg_90d_usd)
        updated_avg = round((prev_avg * 0.85) + (current_price_usd * 0.15), 2)

        is_new_drop = (
            last_pub is None
            or current_price_usd <= float(last_pub) - min_drop_delta_usd
        )
        price_delta = round(current_price_usd - prev_price, 2)

        prev["last_price_usd"] = round(current_price_usd, 2)
        prev["min_price_seen_usd"] = round(min_seen, 2)
        prev["avg_90d_usd"] = round(updated_avg, 2)
        prev["last_seen_at"] = now_iso

        return {
            "is_new_drop": is_new_drop,
            "previous_price_usd": prev_price,
            "price_delta_usd": price_delta,
            "is_all_time_low_seen": current_price_usd <= min_seen,
        }

    def mark_published(self, asin: str, price_usd: float) -> None:
        asin_key = asin.upper()
        if asin_key in self.records:
            self.records[asin_key]["last_published_price_usd"] = round(price_usd, 2)
            self.records[asin_key]["last_published_at"] = datetime.now(timezone.utc).isoformat()
