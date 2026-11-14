"""Generador determinista (0 tokens LLM) de tarjetas HD 1080x1080 con marca de agua PillePues para Telegram."""

from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Any

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore[assignment]

from urllib import request as urllib_request

try:
    from PIL import Image, ImageDraw, ImageFont, ImageOps  # type: ignore

    HAS_PIL = True
except ImportError:  # pragma: no cover
    Image = None  # type: ignore[assignment]
    ImageDraw = None  # type: ignore[assignment]
    ImageFont = None  # type: ignore[assignment]
    ImageOps = None  # type: ignore[assignment]
    HAS_PIL = False


_AMAZON_IMG_SIZE_RE = re.compile(
    r"(https://(?:m\.media-amazon\.com|images-na\.ssl-images-amazon\.com)/images/I/[^/.]+)\._[^/]+_\.(jpg|jpeg|png|webp)$",
    re.IGNORECASE,
)

_FONT_BOLD_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/opentype/urw-base35/NimbusSans-Bold.otf",
)

_FONT_REGULAR_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/opentype/urw-base35/NimbusSans-Regular.otf",
)

_BRAND_LOGO_PATH = Path(__file__).resolve().parent.parent.parent / "public" / "assets" / "pillepues-logo.png"


def _load_brand_logo(max_size: int) -> Any | None:
    """Carga y escala el logo oficial de PillePues (RGBA transparente) si existe en disco."""
    if not HAS_PIL or Image is None or not _BRAND_LOGO_PATH.exists():
        return None
    try:
        resample = getattr(Image, "Resampling", Image).LANCZOS
        with Image.open(_BRAND_LOGO_PATH) as raw_logo:
            logo = raw_logo.convert("RGBA")
            logo.thumbnail((max_size, max_size), resample)
            return logo
    except Exception:
        return None


def upgrade_amazon_image_url(image_url: str, size: int = 1500) -> str:
    """Convierte miniaturas de Amazon (`_AC_UL320_`, `_SX300_`, etc.) a alta resolución (`_AC_SL1500_`) sin degradar imágenes HD."""
    raw = (image_url or "").strip()
    if not raw:
        return ""
    existing_sl = re.search(r"\._AC_SL(\d+)_\.", raw, re.IGNORECASE)
    if existing_sl and int(existing_sl.group(1)) >= int(size):
        return raw
    match = _AMAZON_IMG_SIZE_RE.match(raw)
    if match:
        base, ext = match.group(1), match.group(2)
        return f"{base}._AC_SL{int(size)}_.{ext}"
    return raw


def build_image_url_candidates(image_url: str) -> list[str]:
    """Genera URLs candidatas ordenadas de mayor a menor resolución para descarga segura."""
    raw = (image_url or "").strip()
    if not raw:
        return []
    candidates: list[str] = []
    match = _AMAZON_IMG_SIZE_RE.match(raw)
    if match:
        base, ext = match.group(1), match.group(2)
        candidates.extend(
            [
                f"{base}._AC_SL1500_.{ext}",
                f"{base}._AC_SL1200_.{ext}",
                f"{base}.{ext}",
            ]
        )
    if raw not in candidates:
        candidates.append(raw)
    return candidates


def _load_font(size: int, bold: bool = False) -> Any:
    if ImageFont is None:
        return None
    paths = _FONT_BOLD_CANDIDATES if bold else _FONT_REGULAR_CANDIDATES
    for path_str in paths:
        if Path(path_str).exists():
            try:
                return ImageFont.truetype(path_str, size=size)
            except Exception:
                continue
    return ImageFont.load_default()


def _download_image_bytes(url: str, timeout: float = 10.0) -> bytes | None:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        ),
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    }
    for candidate in build_image_url_candidates(url):
        if httpx is not None:
            try:
                with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                    resp = client.get(candidate, headers=headers)
                    if resp.status_code == 200 and resp.content and len(resp.content) > 512:
                        return resp.content
            except Exception:
                pass
        try:
            req = urllib_request.Request(candidate, headers=headers)
            with urllib_request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    data = resp.read()
                    if data and len(data) > 512:
                        return data
        except Exception:
            pass
    return None


def _trim_white_margin(img: "Image.Image", threshold: int = 247, padding: int = 12) -> "Image.Image":
    """Recorta únicamente el borde blanco sobrante sin cortar jamás ninguna parte del producto."""
    rgb = img.convert("RGB")
    w, h = rgb.size
    if w < 20 or h < 20:
        return img
    # Detectar píxeles no blancos
    mask = rgb.point(lambda p: 255 if p < threshold else 0).convert("L")
    bbox = mask.getbbox()
    if not bbox:
        return img
    left, top, right, bottom = bbox
    if (right - left) < w * 0.15 or (bottom - top) < h * 0.15:
        return img
    left = max(0, left - padding)
    top = max(0, top - padding)
    right = min(w, right + padding)
    bottom = min(h, bottom + padding)
    return img.crop((left, top, right, bottom))


def _wrap_text(draw: "ImageDraw.ImageDraw", text: str, font: Any, max_width: int, max_lines: int = 2) -> list[str]:
    words = (text or "").split()
    if not words:
        return []
    lines: list[str] = []
    current = ""
    for idx, word in enumerate(words):
        candidate = f"{current} {word}".strip() if current else word
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if (bbox[2] - bbox[0]) <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
            if len(lines) >= max_lines - 1:
                remaining = " ".join([current] + words[idx + 1 :]).strip()
                while remaining:
                    tb = draw.textbbox((0, 0), remaining + "...", font=font)
                    if (tb[2] - tb[0]) <= max_width or len(remaining) <= 6:
                        break
                    remaining = remaining[:-1].rstrip()
                if remaining != " ".join([current] + words[idx + 1 :]).strip():
                    remaining = remaining.rstrip(".,;:- ") + "..."
                lines.append(remaining)
                current = ""
                break
    if current and len(lines) < max_lines:
        lines.append(current)
    return lines[:max_lines]


def render_offer_card_from_image_bytes(
    image_bytes: bytes,
    deal: dict[str, Any],
    brand_name: str = "PillePues",
    channel_handle: str = "@pillepues",
) -> bytes:
    """
    Compone una tarjeta PNG HD (1080x1080) alrededor de la foto real del producto usando `contain`
    con amplio margen (nunca recortada), información de precio/descuento y marca de agua PillePues.
    """
    if not HAS_PIL or Image is None or ImageDraw is None or ImageOps is None:
        return image_bytes

    resample_lanczos = getattr(Image, "Resampling", Image).LANCZOS

    with Image.open(io.BytesIO(image_bytes)) as src_raw:
        src_rgba = src_raw.convert("RGBA")
        white_bg = Image.new("RGBA", src_rgba.size, (255, 255, 255, 255))
        product_img = Image.alpha_composite(white_bg, src_rgba).convert("RGB")
        product_img = _trim_white_margin(product_img)

    W, H = 1080, 1080
    canvas = Image.new("RGBA", (W, H), (241, 245, 249, 255))  # #F1F5F9
    draw = ImageDraw.Draw(canvas)

    # 1. Header oscuro editorial + barra tricolor Colombia
    header_h = 126
    draw.rectangle([(0, 0), (W, header_h)], fill=(15, 23, 42, 255))  # #0F172A
    draw.rectangle([(0, 0), (int(W * 0.50), 8)], fill=(250, 204, 21, 255))   # Amarillo CO
    draw.rectangle([(int(W * 0.50), 0), (int(W * 0.75), 8)], fill=(37, 99, 235, 255))   # Azul CO
    draw.rectangle([(int(W * 0.75), 0), (W, 8)], fill=(220, 38, 38, 255))    # Rojo CO

    font_brand = _load_font(40, bold=True)
    font_subbrand = _load_font(22, bold=True)
    font_discount = _load_font(36, bold=True)
    font_pill = _load_font(21, bold=True)
    font_title = _load_font(30, bold=True)
    font_price = _load_font(46, bold=True)
    font_strike = _load_font(25, bold=False)
    font_cop = _load_font(27, bold=True)
    font_watermark = _load_font(28, bold=True)
    font_stamp = _load_font(20, bold=True)

    logo_header = _load_brand_logo(98)
    if logo_header is not None:
        lx = 32
        ly = 12 + (header_h - 12 - logo_header.height) // 2
        canvas.alpha_composite(logo_header, (lx, ly))
        draw = ImageDraw.Draw(canvas)
        sub_x = lx + logo_header.width + 18
        draw.text((sub_x, 24), f"{brand_name} · OFERTAS BIEN BACANAS", font=_load_font(28, bold=True), fill=(250, 204, 21, 255))
        draw.text((sub_x, 60), "OFERTAS VERIFICADAS AMAZON -> COLOMBIA", font=_load_font(19, bold=True), fill=(248, 250, 252, 255))
        draw.text((sub_x, 88), f"{channel_handle} · Envío directo sin casillero", font=_load_font(19, bold=False), fill=(148, 163, 184, 255))
    else:
        # Fallback textual si no está el asset del logo
        brand_bbox = draw.textbbox((0, 0), brand_name, font=font_brand)
        brand_w = (brand_bbox[2] - brand_bbox[0]) + 40
        brand_x0, brand_y0 = 36, 30
        brand_x1, brand_y1 = brand_x0 + brand_w, 98
        draw.rounded_rectangle([(brand_x0, brand_y0), (brand_x1, brand_y1)], radius=14, fill=(245, 158, 11, 255))
        brand_tx = brand_x0 + 20 - brand_bbox[0]
        brand_ty = brand_y0 + ((brand_y1 - brand_y0) - (brand_bbox[3] - brand_bbox[1])) // 2 - brand_bbox[1]
        draw.text((brand_tx, brand_ty), brand_name, font=font_brand, fill=(15, 23, 42, 255))

        sub_x = brand_x1 + 22
        draw.text((sub_x, 36), "OFERTAS AMAZON · COLOMBIA", font=font_subbrand, fill=(248, 250, 252, 255))
        draw.text((sub_x, 68), f"{channel_handle} · Envío directo sin casillero", font=_load_font(20, bold=False), fill=(148, 163, 184, 255))

    # Badge derecha: -XX% OFF
    discount_pct = int(round(float(deal.get("discount_pct") or 0)))
    disc_text = f"-{discount_pct}% OFF" if discount_pct > 0 else "OFERTA"
    disc_bbox = draw.textbbox((0, 0), disc_text, font=font_discount)
    disc_w = (disc_bbox[2] - disc_bbox[0]) + 44
    disc_x1 = W - 36
    disc_x0 = disc_x1 - disc_w
    draw.rounded_rectangle([(disc_x0, 32), (disc_x1, 100)], radius=16, fill=(220, 38, 38, 255))
    disc_tx = disc_x0 + 22 - disc_bbox[0]
    disc_ty = 32 + (68 - (disc_bbox[3] - disc_bbox[1])) // 2 - disc_bbox[1]
    draw.text((disc_tx, disc_ty), disc_text, font=font_discount, fill=(255, 255, 255, 255))

    # 2. Vitrina blanca centrada para el producto (NUNCA recortado)
    stage_x0, stage_y0 = 36, 142
    stage_x1, stage_y1 = W - 36, 786
    draw.rounded_rectangle(
        [(stage_x0, stage_y0), (stage_x1, stage_y1)],
        radius=28,
        fill=(255, 255, 255, 255),
        outline=(203, 213, 225, 255),
        width=2,
    )

    inner_pad_x = 68
    inner_pad_top = 44
    inner_pad_bottom = 78
    max_prod_w = (stage_x1 - stage_x0) - (inner_pad_x * 2)
    max_prod_h = (stage_y1 - stage_y0) - inner_pad_top - inner_pad_bottom

    fitted = ImageOps.contain(product_img, (max_prod_w, max_prod_h), method=resample_lanczos)
    px = stage_x0 + inner_pad_x + (max_prod_w - fitted.width) // 2
    py = stage_y0 + inner_pad_top + (max_prod_h - fitted.height) // 2
    canvas.paste(fitted.convert("RGBA"), (px, py))

    # 3. Marca de agua diagonal sutil PillePues sobre el área de vitrina (protege sin tapar)
    wm_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    wm_tile = Image.new("RGBA", (420, 120), (0, 0, 0, 0))
    wm_draw = ImageDraw.Draw(wm_tile)
    wm_draw.text((16, 40), f"{brand_name} · {channel_handle}", font=font_watermark, fill=(15, 23, 42, 20))
    resample_bicubic = getattr(Image, "Resampling", Image).BICUBIC
    wm_rotated = wm_tile.rotate(24, expand=True, resample=resample_bicubic)
    for wy in (176, 382):
        for wx in (90, 520):
            wm_layer.alpha_composite(wm_rotated, (wx, wy))
    # Recortar la marca de agua solo dentro de la vitrina (encima de la franja de badges)
    stage_mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(stage_mask).rounded_rectangle(
        [(stage_x0 + 4, stage_y0 + 4), (stage_x1 - 4, stage_y1 - 60)],
        radius=26,
        fill=255,
    )
    canvas = Image.composite(Image.alpha_composite(canvas, wm_layer), canvas, stage_mask)
    draw = ImageDraw.Draw(canvas)

    # Sello visible de marca en esquina inferior derecha (con mini-mascota + texto)
    stamp_text = f"{brand_name} · {channel_handle}"
    logo_stamp = _load_brand_logo(26)
    icon_slot = (logo_stamp.width + 8) if logo_stamp is not None else 0
    st_bbox = draw.textbbox((0, 0), stamp_text, font=font_stamp)
    st_w = (st_bbox[2] - st_bbox[0]) + 28 + icon_slot
    st_x1 = stage_x1 - 22
    st_x0 = st_x1 - st_w
    pill_y0, pill_y1 = stage_y1 - 52, stage_y1 - 14
    draw.rounded_rectangle(
        [(st_x0, pill_y0), (st_x1, pill_y1)],
        radius=12,
        fill=(15, 23, 42, 238),
        outline=(245, 158, 11, 255),
        width=2,
    )
    if logo_stamp is not None:
        logo_sy = pill_y0 + ((pill_y1 - pill_y0) - logo_stamp.height) // 2
        canvas.alpha_composite(logo_stamp, (st_x0 + 10, logo_sy))
        draw = ImageDraw.Draw(canvas)
    st_ty = pill_y0 + ((pill_y1 - pill_y0) - (st_bbox[3] - st_bbox[1])) // 2 - st_bbox[1]
    draw.text((st_x0 + 14 + icon_slot - st_bbox[0], st_ty), stamp_text, font=font_stamp, fill=(254, 243, 199, 255))

    # Badges inferiores izquierda dentro de la vitrina (Envío CO + DIAN sin solapamiento)
    ships_direct = bool(deal.get("ships_to_colombia", False)) and not bool(deal.get("requires_locker", False))
    price_usd = float(deal.get("price_usd") or 0.0)
    tax_free = bool(deal.get("tax_free_colombia", price_usd <= 200.0))
    free_ship = bool(deal.get("free_shipping_co", False))

    left_pill_text = (
        "ENVÍO GRATIS A COLOMBIA"
        if (ships_direct and free_ship)
        else ("ENVÍO DIRECTO A COLOMBIA" if ships_direct else "REVISAR ENVÍO COLOMBIA")
    )
    lp_bbox = draw.textbbox((0, 0), left_pill_text, font=font_stamp)
    lp_w = (lp_bbox[2] - lp_bbox[0]) + 28
    lp_x0 = stage_x0 + 22
    lp_x1 = lp_x0 + lp_w
    draw.rounded_rectangle(
        [(lp_x0, pill_y0), (lp_x1, pill_y1)],
        radius=12,
        fill=(236, 253, 245, 245),
        outline=(16, 185, 129, 255),
        width=2,
    )
    lp_ty = pill_y0 + ((pill_y1 - pill_y0) - (lp_bbox[3] - lp_bbox[1])) // 2 - lp_bbox[1]
    draw.text((lp_x0 + 14 - lp_bbox[0], lp_ty), left_pill_text, font=font_stamp, fill=(4, 120, 87, 255))

    if tax_free:
        dian_text = "0% IVA DIAN (<= $200)"
        db_bbox = draw.textbbox((0, 0), dian_text, font=font_stamp)
        db_w = (db_bbox[2] - db_bbox[0]) + 26
        dx0 = lp_x1 + 12
        if dx0 + db_w >= st_x0 - 12:
            dian_text = "0% IVA DIAN"
            db_bbox = draw.textbbox((0, 0), dian_text, font=font_stamp)
            db_w = (db_bbox[2] - db_bbox[0]) + 26
        if dx0 + db_w < st_x0 - 12:
            draw.rounded_rectangle(
                [(dx0, pill_y0), (dx0 + db_w, pill_y1)],
                radius=12,
                fill=(239, 246, 255, 245),
                outline=(59, 130, 246, 255),
                width=2,
            )
            db_ty = pill_y0 + ((pill_y1 - pill_y0) - (db_bbox[3] - db_bbox[1])) // 2 - db_bbox[1]
            draw.text((dx0 + 13 - db_bbox[0], db_ty), dian_text, font=font_stamp, fill=(29, 78, 216, 255))

    # 4. Panel inferior editorial: Título + Precio USD / Antes / COP
    footer_x0, footer_y0 = 36, 804
    footer_x1, footer_y1 = W - 36, H - 28
    draw.rounded_rectangle(
        [(footer_x0, footer_y0), (footer_x1, footer_y1)],
        radius=24,
        fill=(255, 255, 255, 255),
        outline=(203, 213, 225, 255),
        width=2,
    )

    title_lines = _wrap_text(
        draw,
        str(deal.get("title") or "Oferta verificada Amazon.com"),
        font=font_title,
        max_width=(footer_x1 - footer_x0) - 56,
        max_lines=2,
    )
    ty = footer_y0 + 22
    for line in title_lines:
        draw.text((footer_x0 + 28, ty), line, font=font_title, fill=(15, 23, 42, 255))
        ty += 38

    # Línea divisoria sutil
    div_y = footer_y0 + 114
    draw.line([(footer_x0 + 28, div_y), (footer_x1 - 28, div_y)], fill=(226, 232, 240, 255), width=2)

    # Precio USD + Precio Anterior tachado
    price_text = f"${price_usd:.2f} USD"
    draw.text((footer_x0 + 28, div_y + 22), price_text, font=font_price, fill=(15, 23, 42, 255))
    p_bbox = draw.textbbox((footer_x0 + 28, div_y + 22), price_text, font=font_price)

    ref_price = float(
        deal.get("reference_price_usd")
        or deal.get("avg_90d_usd")
        or deal.get("list_price_usd")
        or price_usd
    )
    if ref_price > price_usd:
        strike_text = f"Antes ${ref_price:.2f}"
        sx = p_bbox[2] + 20
        sy = div_y + 38
        draw.text((sx, sy), strike_text, font=font_strike, fill=(100, 116, 139, 255))
        s_bbox = draw.textbbox((sx, sy), strike_text, font=font_strike)
        mid_y = (s_bbox[1] + s_bbox[3]) // 2
        draw.line([(s_bbox[0] - 2, mid_y), (s_bbox[2] + 2, mid_y)], fill=(220, 38, 38, 230), width=3)

    # Precio COP a la derecha
    trm = float(deal.get("trm_cop") or 4150.0)
    price_cop = float(deal.get("price_cop") or round(price_usd * trm))
    cop_str = f"~${int(round(price_cop)):,}".replace(",", ".") + " COP"
    cop_bbox = draw.textbbox((0, 0), cop_str, font=font_cop)
    cop_w = (cop_bbox[2] - cop_bbox[0]) + 36
    cop_x1 = footer_x1 - 28
    cop_x0 = cop_x1 - cop_w
    draw.rounded_rectangle(
        [(cop_x0, div_y + 20), (cop_x1, div_y + 76)],
        radius=14,
        fill=(236, 253, 245, 255),
        outline=(16, 185, 129, 255),
        width=2,
    )
    draw.text((cop_x0 + 18, div_y + 32), cop_str, font=font_cop, fill=(4, 120, 87, 255))

    # Sub-pie inferior
    savings_usd = max(0.0, ref_price - price_usd)
    sub_left = (
        f"Ahorras ${savings_usd:.2f} USD · Link oficial Amazon Associates (pillepues-20)"
        if savings_usd >= 1.0
        else "Oferta verificada Amazon.com -> Colombia (pillepues-20)"
    )
    draw.text((footer_x0 + 28, div_y + 88), sub_left, font=_load_font(19, bold=False), fill=(100, 116, 139, 255))

    out_buf = io.BytesIO()
    canvas.convert("RGB").save(out_buf, format="JPEG", quality=93, optimize=True)
    return out_buf.getvalue()


def render_telegram_offer_card_bytes(
    photo_url: str,
    deal: dict[str, Any] | None = None,
    timeout: float = 10.0,
) -> bytes | None:
    """Descarga la foto HD del producto y renderiza la tarjeta PillePues lista para `sendPhoto`."""
    if not HAS_PIL or not photo_url or not str(photo_url).strip().lower().startswith(("https://", "http://")):
        return None
    raw_bytes = _download_image_bytes(photo_url, timeout=timeout)
    if not raw_bytes:
        return None
    try:
        return render_offer_card_from_image_bytes(raw_bytes, deal=deal or {})
    except Exception:
        return None
