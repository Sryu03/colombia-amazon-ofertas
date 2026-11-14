"""Broadcaster para Telegram (Bot API) y generación de outbox JSON para la web.

Implementa la difusión hacia el canal de Telegram (`@pillepues`) con soporte para envío en vivo
y modo `simulated_outbox` (`status="simulated_ready"`) que persiste las tarjetas generadas
en disco para previsualización en la aplicación web.
"""

from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib import request as urllib_request

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore[assignment]

COLOMBIA_TZ = timezone(timedelta(hours=-5), name="America/Bogota")

# Ventanas de máxima conversión en Colombia (GMT-5):
# 07:00-09:00, 12:00-14:00, 18:00-22:00
COLOMBIA_PEAK_WINDOWS: tuple[tuple[int, int], ...] = (
    (7, 9),
    (12, 14),
    (18, 22),
)

_BOT_TOKEN_URL_RE = re.compile(r"bot\d+:[A-Za-z0-9_-]+")


def _sanitize_error_detail(detail: str, token: str = "") -> str:
    """Elimina cualquier token de Telegram de mensajes de error antes de guardarlos en JSON."""
    cleaned = _BOT_TOKEN_URL_RE.sub("bot<REDACTED>", detail or "")
    if token:
        cleaned = cleaned.replace(token, "<REDACTED>")
    return cleaned


class ChannelBroadcaster:
    """Publicador de ofertas para canal de Telegram."""

    MIN_TELEGRAM_INTERVAL_SECONDS: float = 3.0

    def __init__(
        self,
        telegram_bot_token: str | None = None,
        telegram_chat_id: str = "@pillepues",
        outbox_path: str = "/home/antigravity/amazon-colombia-affiliates/public/data/outbox_cards.json",
    ) -> None:
        self.telegram_bot_token: str | None = (
            telegram_bot_token
            if telegram_bot_token is not None
            else os.getenv("TELEGRAM_BOT_TOKEN")
        )
        self.telegram_chat_id: str = (
            telegram_chat_id
            or os.getenv("TELEGRAM_CHAT_ID", "@pillepues")
        )
        self.outbox_path: str = outbox_path
        self._last_telegram_sent_at: float = 0.0

    @staticmethod
    def is_colombia_peak_hour(dt: datetime | None = None) -> bool:
        """Indica si el momento dado (o actual) está en ventana de alta conversión en Colombia (GMT-5)."""
        now_co = (dt or datetime.now(COLOMBIA_TZ)).astimezone(COLOMBIA_TZ)
        hour = now_co.hour
        return any(start <= hour < end for start, end in COLOMBIA_PEAK_WINDOWS)

    @staticmethod
    def _post_json(url: str, payload: dict[str, Any], timeout: float = 10.0) -> tuple[int, Any]:
        """Envía una petición HTTP POST JSON usando `httpx` (o `urllib` como respaldo)."""
        if httpx is not None:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                try:
                    return response.status_code, response.json()
                except Exception:
                    return response.status_code, response.text

        body = json.dumps(payload).encode("utf-8")
        req = urllib_request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib_request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                return resp.status, json.loads(raw)
            except Exception:
                return resp.status, raw

    @staticmethod
    def _post_photo_bytes_multipart(
        endpoint: str,
        payload: dict[str, Any],
        img_bytes: bytes,
        content_type: str = "image/jpeg",
        timeout: float = 15.0,
    ) -> tuple[int, Any]:
        """Sube bytes de una imagen renderizada o descargada como multipart/form-data a Telegram."""
        if httpx is None:
            raise RuntimeError("httpx no está disponible para subida multipart de imagen")

        form_data: dict[str, str] = {
            "chat_id": str(payload.get("chat_id", "")),
            "caption": str(payload.get("caption", "")),
            "parse_mode": str(payload.get("parse_mode", "HTML")),
        }
        if payload.get("reply_markup") is not None:
            form_data["reply_markup"] = json.dumps(payload["reply_markup"], ensure_ascii=False)

        ext = "png" if "png" in content_type.lower() else "webp" if "webp" in content_type.lower() else "jpg"
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.post(
                endpoint,
                data=form_data,
                files={"photo": (f"pillepues_deal.{ext}", img_bytes, content_type)},
            )
            response.raise_for_status()
            try:
                return response.status_code, response.json()
            except Exception:
                return response.status_code, response.text

    @classmethod
    def _post_photo_multipart(
        cls,
        endpoint: str,
        payload: dict[str, Any],
        photo_url: str,
        timeout: float = 15.0,
    ) -> tuple[int, Any]:
        """Descarga la imagen en memoria y la sube como multipart a Telegram si la URL directa falla."""
        if httpx is None:
            raise RuntimeError("httpx no está disponible para descarga/subida multipart de imagen")

        from src.broadcaster.card_image import build_image_url_candidates

        img_headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            ),
            "Accept": "image/*,*/*;q=0.8",
        }
        img_bytes = b""
        content_type = "image/jpeg"
        last_exc: Exception | None = None
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            for candidate_url in build_image_url_candidates(photo_url):
                try:
                    img_resp = client.get(candidate_url, headers=img_headers)
                    img_resp.raise_for_status()
                    if img_resp.content:
                        img_bytes = img_resp.content
                        content_type = img_resp.headers.get("content-type", "image/jpeg").split(";")[0].strip()
                        break
                except Exception as exc:
                    last_exc = exc
        if not img_bytes:
            if last_exc is not None:
                raise last_exc
            raise RuntimeError("Imagen descargada vacía")

        return cls._post_photo_bytes_multipart(
            endpoint=endpoint,
            payload=payload,
            img_bytes=img_bytes,
            content_type=content_type,
            timeout=timeout,
        )

    def _build_telegram_request(self, telegram_card: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """Construye el método de Telegram Bot API (`sendPhoto` o `sendMessage`) y su payload."""
        from src.broadcaster.card_image import upgrade_amazon_image_url

        chat_id = telegram_card.get("chat_id") or self.telegram_chat_id
        raw_photo_url = (
            telegram_card.get("photo_url")
            or telegram_card.get("photo")
            or telegram_card.get("image_url")
            or ""
        )
        photo_url = upgrade_amazon_image_url(str(raw_photo_url), size=1200) if isinstance(raw_photo_url, str) else ""
        caption = (
            telegram_card.get("caption_html")
            or telegram_card.get("caption")
            or telegram_card.get("text")
            or ""
        )
        parse_mode = telegram_card.get("parse_mode") or "HTML"
        reply_markup = telegram_card.get("reply_markup")

        if reply_markup is None and "inline_keyboard" in telegram_card:
            reply_markup = {"inline_keyboard": telegram_card["inline_keyboard"]}

        is_http_photo = isinstance(photo_url, str) and photo_url.strip().lower().startswith(("https://", "http://"))

        if not is_http_photo:
            api_method = "sendMessage"
            payload: dict[str, Any] = {
                "chat_id": chat_id,
                "text": str(caption)[:4096],
                "parse_mode": parse_mode,
            }
            if isinstance(raw_photo_url, str) and raw_photo_url.strip().startswith("data:"):
                payload["photo_url"] = raw_photo_url
        else:
            api_method = "sendPhoto"
            payload = {
                "chat_id": chat_id,
                "photo": photo_url.strip(),
                "caption": str(caption)[:1024],
                "parse_mode": parse_mode,
            }

        if reply_markup is not None:
            payload["reply_markup"] = reply_markup

        return api_method, payload

    def send_telegram(
        self,
        telegram_card: dict[str, Any],
        deal: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Envía una tarjeta de oferta al canal de Telegram o retorna el payload en modo `simulated_outbox`."""
        api_method, payload = self._build_telegram_request(telegram_card)
        token = (self.telegram_bot_token or "").strip()

        if not token:
            return {
                "channel": "telegram",
                "mode": "simulated_outbox",
                "status": "simulated_ready",
                "token_configured": False,
                "api_method": api_method,
                "endpoint": f"https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/{api_method}",
                "payload": payload,
                "card": telegram_card,
                "fallback_reason": "TELEGRAM_BOT_TOKEN no configurado",
            }

        # Control de rate-limit: máximo 1 mensaje cada 3 segundos en Telegram
        elapsed = time.monotonic() - self._last_telegram_sent_at
        if self._last_telegram_sent_at > 0 and elapsed < self.MIN_TELEGRAM_INTERVAL_SECONDS:
            time.sleep(self.MIN_TELEGRAM_INTERVAL_SECONDS - elapsed)

        endpoint = f"https://api.telegram.org/bot{token}/{api_method}"
        http_payload = {k: v for k, v in payload.items() if k != "photo_url"}
        deal_context = deal or telegram_card.get("deal_snapshot") or {
            "asin": telegram_card.get("asin", ""),
            "title": telegram_card.get("title", ""),
        }

        # 1. Intentar renderizar tarjeta HD 1080x1080 con marca de agua PillePues y producto sin recortes
        if api_method == "sendPhoto" and isinstance(payload.get("photo"), str):
            try:
                from src.broadcaster.card_image import render_telegram_offer_card_bytes

                rendered_bytes = render_telegram_offer_card_bytes(
                    photo_url=payload["photo"],
                    deal=deal_context,
                    timeout=10.0,
                )
                if rendered_bytes:
                    status_code, data = self._post_photo_bytes_multipart(
                        endpoint=endpoint,
                        payload=http_payload,
                        img_bytes=rendered_bytes,
                        content_type="image/jpeg",
                        timeout=15.0,
                    )
                    self._last_telegram_sent_at = time.monotonic()
                    return {
                        "channel": "telegram",
                        "mode": "live",
                        "status": "sent",
                        "token_configured": True,
                        "upload_mode": "rendered_pillepues_card",
                        "http_status": status_code,
                        "api_method": api_method,
                        "payload": payload,
                        "response": data,
                        "card": telegram_card,
                    }
            except Exception:
                # Si falla la composición o subida de la tarjeta renderizada, continuar al flujo estándar
                pass

        try:
            status_code, data = self._post_json(endpoint, http_payload, timeout=10.0)
            self._last_telegram_sent_at = time.monotonic()
            return {
                "channel": "telegram",
                "mode": "live",
                "status": "sent",
                "token_configured": True,
                "http_status": status_code,
                "api_method": api_method,
                "payload": payload,
                "response": data,
                "card": telegram_card,
            }
        except Exception as exc:
            # Si sendPhoto por URL externa falla (p.ej. hotlink bloqueado), intentar descarga + subida multipart
            if api_method == "sendPhoto" and isinstance(payload.get("photo"), str):
                try:
                    status_code, data = self._post_photo_multipart(
                        endpoint=endpoint,
                        payload=http_payload,
                        photo_url=payload["photo"],
                        timeout=15.0,
                    )
                    self._last_telegram_sent_at = time.monotonic()
                    return {
                        "channel": "telegram",
                        "mode": "live",
                        "status": "sent",
                        "token_configured": True,
                        "upload_mode": "multipart",
                        "http_status": status_code,
                        "api_method": api_method,
                        "payload": payload,
                        "response": data,
                        "card": telegram_card,
                    }
                except Exception as mp_exc:
                    exc = mp_exc

            err_detail = str(exc)
            resp = getattr(exc, "response", None)
            if resp is not None and getattr(resp, "text", None):
                err_detail = f"{err_detail} | body={resp.text[:300]}"
            elif hasattr(exc, "read"):
                try:
                    err_detail = f"{err_detail} | body={exc.read().decode('utf-8', errors='replace')[:300]}"
                except Exception:
                    pass
            return {
                "channel": "telegram",
                "mode": "simulated_outbox",
                "status": "simulated_ready",
                "token_configured": True,
                "api_method": api_method,
                "payload": payload,
                "card": telegram_card,
                "fallback_reason": _sanitize_error_detail(err_detail, token=token),
            }

    def broadcast_deal(
        self,
        deal: dict[str, Any],
        telegram_card: dict[str, Any],
    ) -> dict[str, Any]:
        """Publica la oferta en Telegram y guarda el historial en `self.outbox_path`."""
        now_utc = datetime.now(timezone.utc)
        now_co = now_utc.astimezone(COLOMBIA_TZ)

        telegram_result = self.send_telegram(telegram_card, deal=deal)

        entry: dict[str, Any] = {
            "asin": deal.get("asin") or telegram_card.get("asin") or "",
            "title": deal.get("title") or telegram_card.get("title") or "",
            "timestamp": now_utc.isoformat(),
            "timestamp_colombia": now_co.isoformat(),
            "is_colombia_peak_hour": self.is_colombia_peak_hour(now_co),
            "deal": deal,
            "telegram": telegram_result,
            "telegram_card": telegram_card,
        }

        cards = self.get_outbox_cards()
        asin = entry["asin"]
        if asin:
            cards = [c for c in cards if c.get("asin") != asin]
        cards.insert(0, entry)

        outbox_file = Path(self.outbox_path)
        outbox_file.parent.mkdir(parents=True, exist_ok=True)
        outbox_file.write_text(
            json.dumps(cards, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return entry

    def get_outbox_cards(self) -> list[dict[str, Any]]:
        """Lee y devuelve la lista de tarjetas almacenadas en `self.outbox_path`."""
        outbox_file = Path(self.outbox_path)
        if not outbox_file.exists():
            return []
        try:
            raw = outbox_file.read_text(encoding="utf-8").strip()
            if not raw:
                return []
            data = json.loads(raw)
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and isinstance(data.get("cards"), list):
                return data["cards"]
            return []
        except Exception:
            return []
