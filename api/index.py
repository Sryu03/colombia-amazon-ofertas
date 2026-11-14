"""FastAPI Serverless Orchestrator & Local Server for Amazon Colombia Affiliates (Vercel-ready)."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.auditor.deal_auditor import DealAuditor
from src.broadcaster.channels import ChannelBroadcaster
from src.copywriter.affiliate_builder import (
    build_affiliate_url,
    build_telegram_card,
    build_vercel_deal_url,
)
from src.db.database import Database
from src.evaluator.colombia_rules import (
    deal_priority_key,
    evaluate_colombia_deal,
    fetch_live_trm_cop,
)
from src.monitor.amazon_scraper import AmazonMonitorScraper
from src.monitor.discovery import (
    discover_deals_and_asins,
    load_watchlist_asins,
    save_watchlist_asins,
)
from src.monitor.price_history import PriceHistoryStore
from src.monitor.price_watcher import detect_price_drop

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PUBLIC_DIR = PROJECT_ROOT / "public"
DATA_DIR = PUBLIC_DIR / "data"
DB_PATH = str(PROJECT_ROOT / "data" / "deals.db")
WATCHLIST_PATH = PROJECT_ROOT / "data" / "watchlist.json"
PRICE_HISTORY_PATH = DATA_DIR / "price_history.json"

ASSOCIATE_TAG = os.getenv("AMAZON_ASSOCIATE_TAG", "pillepues-20")
PUBLIC_WEB_URL = os.getenv("PUBLIC_WEB_URL", "https://vitrina-colombia-ofertas.vercel.app")
DEFAULT_TRM_COP = float(os.getenv("DEFAULT_TRM_COP", "4150.0"))
MIN_DISCOUNT_PCT = float(os.getenv("MIN_DISCOUNT_PERCENT", "20.0"))
LIVE_SCRAPE = os.getenv("LIVE_SCRAPE", "false").lower() in ("1", "true", "yes")
DISCOVERY_ENABLED = os.getenv("DISCOVERY_ENABLED", "true").lower() in ("1", "true", "yes")
MAX_LIVE_ASINS = int(os.getenv("MAX_LIVE_ASINS", "60"))
MAX_TELEGRAM_PER_CYCLE = int(os.getenv("MAX_TELEGRAM_PER_CYCLE", "5"))
PUBLISH_VERIFIED_CATALOG = os.getenv("PUBLISH_VERIFIED_CATALOG", "false").lower() in ("1", "true", "yes")
MAX_UNVERIFIED_DEAL_AGE_MINUTES = int(os.getenv("MAX_UNVERIFIED_DEAL_AGE_MINUTES", "90"))
ALLOW_LOCKER_DEALS = os.getenv("ALLOW_LOCKER_DEALS", "false").lower() in ("1", "true", "yes")

app = FastAPI(
    title="Amazon Colombia Deals & Zero-Token Agentic Tracker",
    description="API Serverless para monitoreo Zero-Token de Amazon.com hacia Colombia (Telegram y Web en Vercel)",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _is_deal_fresh(
    deal: dict,
    fallback_iso: str | None = None,
    max_age_minutes: int = MAX_UNVERIFIED_DEAL_AGE_MINUTES,
) -> bool:
    """Verifica si una oferta guardada fue verificada recientemente para evitar enviar precios vencidos."""
    raw_ts = str(deal.get("verified_at") or fallback_iso or "").strip()
    if not raw_ts:
        return False
    try:
        parsed = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        age_minutes = (datetime.now(timezone.utc) - parsed).total_seconds() / 60.0
        return age_minutes <= float(max_age_minutes)
    except Exception:
        return False


def _load_existing_deal_targets(deals_json_path: Path) -> list[dict]:
    """Lee los ASINs activos actuales de deals.json (con live_verified=False) para re-verificar su precio en vivo."""
    if not deals_json_path.exists():
        return []
    try:
        payload = json.loads(deals_json_path.read_text(encoding="utf-8"))
        deals = payload.get("deals", []) if isinstance(payload, dict) else []
        targets: list[dict] = []
        for item in deals:
            if not isinstance(item, dict):
                continue
            asin = str(item.get("asin") or "").strip().upper()
            if len(asin) == 10 and asin.isalnum():
                targets.append(
                    {
                        "asin": asin,
                        "category": str(item.get("category") or "Tecnología"),
                        "live_verified": False,
                    }
                )
        return targets
    except Exception:
        return []


def _is_valid_verified_deal(deal: dict) -> bool:
    """Valida que una oferta del catálogo cumpla envío directo a Colombia, imagen HTTPS y precio coherente."""
    asin = str(deal.get("asin") or "").strip().upper()
    if len(asin) != 10 or not asin.isalnum():
        return False
    ships_to_colombia = bool(deal.get("ships_to_colombia", False)) and not bool(
        deal.get("requires_locker", False)
    )
    image_url = str(deal.get("image_url") or "").strip().lower()
    has_https_image = image_url.startswith("https://")
    title = str(deal.get("title") or "").strip().lower()
    has_valid_title = bool(title) and not title.startswith("amazon product")
    price_usd = float(deal.get("price_usd") or 0.0)
    ref_price = float(deal.get("reference_price_usd") or deal.get("avg_90d_usd") or deal.get("list_price_usd") or 0.0)
    savings_usd = float(deal.get("savings_usd") or max(0.0, ref_price - price_usd))
    has_coherent_price = price_usd > 0.0 and ref_price > price_usd and savings_usd >= 1.0
    return ships_to_colombia and has_https_image and has_valid_title and has_coherent_price


def _summarize_telegram_delivery(
    broadcast_results: list[dict],
    broadcaster: ChannelBroadcaster,
    source: str,
) -> dict:
    sent_asins = [
        str(r.get("asin"))
        for r in broadcast_results
        if r.get("telegram", {}).get("status") == "sent" and r.get("asin")
    ]
    errors: list[str] = []
    for r in broadcast_results:
        reason = r.get("telegram", {}).get("fallback_reason")
        if reason:
            short_reason = str(reason)[:220]
            if short_reason not in errors:
                errors.append(short_reason)
                if len(errors) >= 3:
                    break
    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "token_configured": bool((broadcaster.telegram_bot_token or "").strip()),
        "chat_id": broadcaster.telegram_chat_id,
        "source": source,
        "attempted": len(broadcast_results),
        "sent": len(sent_asins),
        "simulated": sum(
            1 for r in broadcast_results if r.get("telegram", {}).get("status") != "sent"
        ),
        "sent_asins": sent_asins,
        "errors": errors,
    }


def run_zero_token_pipeline(
    trm_cop: Optional[float] = None,
    publish_verified_catalog: Optional[bool] = None,
    max_telegram_per_cycle: Optional[int] = None,
    broadcaster: Optional[ChannelBroadcaster] = None,
) -> dict:
    """Runs the complete deterministic Zero-Token monitoring, evaluation, copywriting, broadcasting, and web export pipeline."""
    db = Database(db_path=DB_PATH)
    db.init_db()

    active_trm = trm_cop or fetch_live_trm_cop(default_trm=DEFAULT_TRM_COP)
    scraper = AmazonMonitorScraper()
    price_history = PriceHistoryStore(path=PRICE_HISTORY_PATH)
    broadcaster = broadcaster or ChannelBroadcaster(
        outbox_path=str(DATA_DIR / "outbox_cards.json"),
    )
    should_publish_catalog = (
        PUBLISH_VERIFIED_CATALOG
        if publish_verified_catalog is None
        else bool(publish_verified_catalog)
    )
    telegram_limit = (
        MAX_TELEGRAM_PER_CYCLE
        if max_telegram_per_cycle is None
        else max(1, int(max_telegram_per_cycle))
    )

    run_now_iso = datetime.now(timezone.utc).isoformat()
    deals_json_path = DATA_DIR / "deals.json"
    auditor = DealAuditor(
        min_discount_pct=MIN_DISCOUNT_PCT,
        allow_locker_deals=ALLOW_LOCKER_DEALS,
        require_live_detail=LIVE_SCRAPE,
        require_colombia_confirmation=LIVE_SCRAPE,
    )
    watchlist_items = load_watchlist_asins(WATCHLIST_PATH)
    parsed_live_deals: list[dict] = []
    if LIVE_SCRAPE and DISCOVERY_ENABLED:
        existing_asins = {str(item.get("asin", "")).upper() for item in watchlist_items}
        newly_discovered, parsed_live_deals = discover_deals_and_asins(
            existing_asins=existing_asins,
            max_new_asins=30,
            price_history_records=price_history.records,
        )
        if newly_discovered:
            watchlist_items = (newly_discovered + watchlist_items)[:150]
            save_watchlist_asins(WATCHLIST_PATH, watchlist_items)

    existing_deal_targets = _load_existing_deal_targets(deals_json_path) if LIVE_SCRAPE else []
    catalog = scraper.fetch_catalog(
        use_seed=not LIVE_SCRAPE,
        extra_items=parsed_live_deals + existing_deal_targets + watchlist_items,
        max_live_asins=MAX_LIVE_ASINS,
    )
    approved_candidates: list[tuple[dict, dict, dict]] = []
    broadcast_results: list[dict] = []
    new_price_drops_count = 0

    for raw_item in catalog:
        asin = str(raw_item["asin"]).upper()
        raw_item["asin"] = asin
        price_usd = round(float(raw_item.get("price_usd") or 0.0), 2)
        if price_usd <= 0.0:
            continue

        list_price_usd = round(float(raw_item.get("list_price_usd", price_usd) or price_usd), 2)
        baseline_avg = price_history.get_baseline_avg(asin) if LIVE_SCRAPE else None
        avg_90d_usd = round(
            float(
                baseline_avg
                if baseline_avg is not None
                else raw_item.get("avg_90d_usd", list_price_usd)
            ),
            2,
        )
        raw_item["avg_90d_usd"] = avg_90d_usd

        db.upsert_product(raw_item)
        db.record_price(
            asin=asin,
            price_usd=price_usd,
            list_price_usd=list_price_usd,
            avg_90d_usd=avg_90d_usd,
        )

        # Persist price history & check if this is a newly detected price drop
        history_event = price_history.evaluate_and_record(
            asin=asin,
            current_price_usd=price_usd,
            avg_90d_usd=avg_90d_usd,
        )

        # Layer 0: Deterministic Zero-Token Price Drop Check
        drop_info = detect_price_drop(
            current_price=price_usd,
            avg_90d=avg_90d_usd,
            list_price=list_price_usd,
            min_discount_pct=MIN_DISCOUNT_PCT,
            min_savings_usd=1.0,
        )
        if not drop_info["is_deal"]:
            continue

        # Layer 1: Colombia Customs, Shipping & TRM Evaluation (arancel-guardian-analista)
        evaluated = evaluate_colombia_deal(
            product=raw_item,
            trm_cop=active_trm,
            min_discount_pct=MIN_DISCOUNT_PCT,
            allow_locker_deals=ALLOW_LOCKER_DEALS,
        )
        if not evaluated.get("approved_for_colombia", False):
            continue

        # Layer 2: Affiliate Links & Copy Generation (midas-copy-afiliados)
        evaluated["affiliate_url"] = build_affiliate_url(asin, associate_tag=ASSOCIATE_TAG)
        evaluated["web_url"] = build_vercel_deal_url(asin, public_web_url=PUBLIC_WEB_URL)
        evaluated["is_new_price_drop"] = history_event["is_new_drop"]
        evaluated["previous_price_usd"] = history_event["previous_price_usd"]
        evaluated["verified_at"] = run_now_iso

        tg_card = build_telegram_card(
            deal=evaluated,
            associate_tag=ASSOCIATE_TAG,
            public_web_url=PUBLIC_WEB_URL,
        )
        evaluated["telegram_copy"] = tg_card["caption_html"]

        # Layer 2.5: Auditoría Final Obligatoria (verificador-colombia-auditor)
        audit_res = auditor.audit_deal(evaluated, telegram_card=tg_card)
        if not audit_res.approved:
            continue

        evaluated["audited_by"] = "verificador-colombia-auditor"
        approved_candidates.append((evaluated, tg_card, history_event))

    # Priorizar estrictamente por mejor oferta/descuento y envío a Colombia (NO por comisión)
    approved_candidates.sort(key=lambda item: deal_priority_key(item[0]), reverse=True)
    approved_deals: list[dict] = []
    live_sent_count = 0
    telegram_source = "none"

    for evaluated, tg_card, history_event in approved_candidates:
        asin = evaluated["asin"]
        price_usd = evaluated["price_usd"]

        db.save_published_deal(evaluated)
        approved_deals.append(evaluated)

        should_send_live = (
            (history_event["is_new_drop"] and live_sent_count < telegram_limit)
            or not LIVE_SCRAPE
        )
        if should_send_live:
            telegram_source = "live_scrape" if LIVE_SCRAPE else "seed_pipeline"
            b_res = broadcaster.broadcast_deal(
                deal=evaluated,
                telegram_card=tg_card,
            )
            broadcast_results.append(b_res)
            if history_event["is_new_drop"]:
                new_price_drops_count += 1
                live_sent_count += 1
                if b_res.get("telegram", {}).get("status") == "sent":
                    price_history.mark_published(asin, price_usd)

    expired_asins: set[str] = set()
    refreshed_deals_by_asin: dict[str, dict] = {}
    skipped_stale_count = 0

    # Si en la nube el scraping en vivo no logró enviar bajadas nuevas y se solicitó publicar el catálogo verificado
    if should_publish_catalog and live_sent_count == 0 and (approved_deals or deals_json_path.exists()):
        existing_generated_at: str | None = None
        already_fresh_in_run = bool(approved_deals)
        if already_fresh_in_run:
            stored_deals = [dict(d) for d in approved_deals]
            existing_generated_at = run_now_iso
        else:
            try:
                existing_payload = json.loads(deals_json_path.read_text(encoding="utf-8"))
                if isinstance(existing_payload, dict):
                    existing_generated_at = str(existing_payload.get("generated_at") or "") or None
                    stored_deals = existing_payload.get("deals", [])
                else:
                    stored_deals = []
            except Exception:
                stored_deals = []

        verified_pool: list[dict] = []
        for d in stored_deals:
            if not isinstance(d, dict):
                continue
            d_asin = str(d.get("asin") or "").strip().upper()
            audit_cached = auditor.audit_deal(d, record_metrics=False)
            if audit_cached.approved:
                verified_pool.append(dict(d))
            elif d_asin:
                expired_asins.add(d_asin)

        verified_pool.sort(key=deal_priority_key, reverse=True)

        unpublished_pool: list[dict] = []
        for deal_item in verified_pool:
            asin = str(deal_item["asin"]).upper()
            price_usd = round(float(deal_item.get("price_usd") or 0.0), 2)
            rec = price_history.records.get(asin)
            last_pub = rec.get("last_published_price_usd") if isinstance(rec, dict) else None
            if last_pub is None or price_usd <= float(last_pub) - 1.0:
                unpublished_pool.append(deal_item)

        max_checks = max(telegram_limit * 3, 15)
        consecutive_live_blocks = 0
        sent_from_catalog = 0

        for deal_item in unpublished_pool[:max_checks]:
            if sent_from_catalog >= telegram_limit:
                break

            asin = str(deal_item["asin"]).upper()
            stored_avg = round(
                float(deal_item.get("avg_90d_usd") or deal_item.get("reference_price_usd") or deal_item.get("price_usd") or 0.0),
                2,
            )

            # Re-verificación obligatoria en vivo por el Auditor antes de enviar ofertas en cola desde deals.json
            if LIVE_SCRAPE and not already_fresh_in_run:
                live_item = scraper.fetch_asin_live(asin) if consecutive_live_blocks < 4 else None
                if live_item is not None:
                    consecutive_live_blocks = 0
                    if (
                        not live_item.get("live_verified")
                        or float(live_item.get("price_usd") or 0.0) <= 0.0
                        or not live_item.get("has_buybox", True)
                    ):
                        expired_asins.add(asin)
                        auditor.audit_deal(live_item)
                        continue

                    live_price = round(float(live_item["price_usd"]), 2)
                    live_list = round(float(live_item.get("list_price_usd") or live_price), 2)
                    baseline_avg = price_history.get_baseline_avg(asin)
                    candidate_avgs = [v for v in (baseline_avg, stored_avg, live_list) if v and v > 0.0]
                    honest_avg = round(min(candidate_avgs), 2) if candidate_avgs else live_list
                    if live_list > live_price:
                        honest_avg = min(honest_avg, live_list) if honest_avg > live_price else live_list

                    merged = dict(deal_item)
                    merged.update(live_item)
                    merged["asin"] = asin
                    merged["category"] = str(deal_item.get("category") or live_item.get("category") or "Tecnología")
                    merged["avg_90d_usd"] = honest_avg
                    if live_list <= live_price and honest_avg > live_price:
                        merged["list_price_usd"] = honest_avg

                    price_history.evaluate_and_record(
                        asin=asin,
                        current_price_usd=live_price,
                        avg_90d_usd=honest_avg,
                    )

                    drop_info = detect_price_drop(
                        current_price=live_price,
                        avg_90d=honest_avg,
                        list_price=float(merged.get("list_price_usd") or live_price),
                        min_discount_pct=MIN_DISCOUNT_PCT,
                        min_savings_usd=1.0,
                    )
                    re_eval = evaluate_colombia_deal(
                        product=merged,
                        trm_cop=active_trm,
                        min_discount_pct=MIN_DISCOUNT_PCT,
                        allow_locker_deals=ALLOW_LOCKER_DEALS,
                    )
                    re_eval["verified_at"] = run_now_iso
                    re_eval["affiliate_url"] = build_affiliate_url(asin, associate_tag=ASSOCIATE_TAG)
                    re_eval["web_url"] = build_vercel_deal_url(asin, public_web_url=PUBLIC_WEB_URL)
                    re_tg_card = build_telegram_card(
                        deal=re_eval,
                        associate_tag=ASSOCIATE_TAG,
                        public_web_url=PUBLIC_WEB_URL,
                    )
                    re_eval["telegram_copy"] = re_tg_card["caption_html"]
                    re_audit = auditor.audit_deal(re_eval, telegram_card=re_tg_card)

                    if not (
                        drop_info["is_deal"]
                        and re_eval.get("approved_for_colombia", False)
                        and re_audit.approved
                    ):
                        expired_asins.add(asin)
                        continue

                    re_eval["audited_by"] = "verificador-colombia-auditor"
                    refreshed_deals_by_asin[asin] = re_eval
                    deal_item = re_eval
                else:
                    consecutive_live_blocks += 1
                    if not _is_deal_fresh(deal_item, fallback_iso=existing_generated_at):
                        skipped_stale_count += 1
                        continue

            price_usd = round(float(deal_item.get("price_usd") or 0.0), 2)
            avg_90d_usd = round(
                float(deal_item.get("avg_90d_usd") or deal_item.get("reference_price_usd") or price_usd),
                2,
            )
            deal_item["asin"] = asin
            deal_item["affiliate_url"] = build_affiliate_url(asin, associate_tag=ASSOCIATE_TAG)
            deal_item["web_url"] = build_vercel_deal_url(asin, public_web_url=PUBLIC_WEB_URL)
            tg_card = build_telegram_card(
                deal=deal_item,
                associate_tag=ASSOCIATE_TAG,
                public_web_url=PUBLIC_WEB_URL,
            )
            final_tg_audit = auditor.audit_deal(deal_item, telegram_card=tg_card, record_metrics=False)
            if not final_tg_audit.approved:
                expired_asins.add(asin)
                continue

            telegram_source = "verified_catalog"
            b_res = broadcaster.broadcast_deal(
                deal=deal_item,
                telegram_card=tg_card,
            )
            broadcast_results.append(b_res)
            sent_from_catalog += 1
            if b_res.get("telegram", {}).get("status") == "sent":
                if asin not in price_history.records:
                    price_history.evaluate_and_record(
                        asin=asin,
                        current_price_usd=price_usd,
                        avg_90d_usd=avg_90d_usd,
                    )
                price_history.mark_published(asin, price_usd)

        if sent_from_catalog == 0 and skipped_stale_count > 0:
            telegram_source = "stale_catalog_blocked_recheck"

    telegram_delivery_status = _summarize_telegram_delivery(
        broadcast_results=broadcast_results,
        broadcaster=broadcaster,
        source=telegram_source,
    )
    if skipped_stale_count > 0:
        telegram_delivery_status["skipped_stale_unverified"] = skipped_stale_count
    if expired_asins:
        telegram_delivery_status["pruned_expired_asins"] = sorted(expired_asins)

    audit_report = auditor.summary()

    # Layer 3: Export static JSON catalog & price history for Vercel CDN
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    price_history.save()

    if LIVE_SCRAPE and len(approved_deals) == 0 and deals_json_path.exists():
        # Preserve existing public catalog if live discovery yielded 0 approved deals,
        # while strictly purging expired or unaudited items via DealAuditor.
        try:
            preserved = json.loads(deals_json_path.read_text(encoding="utf-8"))
            if isinstance(preserved, dict):
                current_list = preserved.get("deals", [])
                if isinstance(current_list, list):
                    updated_list: list[dict] = []
                    for item in current_list:
                        if not isinstance(item, dict):
                            continue
                        item_asin = str(item.get("asin") or "").upper()
                        if item_asin in expired_asins:
                            continue
                        candidate_item = refreshed_deals_by_asin.get(item_asin, item)
                        if not auditor.audit_deal(candidate_item, record_metrics=False).approved:
                            if item_asin:
                                expired_asins.add(item_asin)
                            continue
                        updated_list.append(candidate_item)
                    preserved["deals"] = updated_list
                    preserved["total_deals"] = len(updated_list)
                    preserved["tax_free_count"] = sum(
                        1 for d in updated_list if d.get("tax_free_colombia", True)
                    )
                    preserved["free_shipping_count"] = sum(
                        1 for d in updated_list if d.get("free_shipping_co", False)
                    )
                    preserved["categories"] = sorted(
                        {str(d.get("category") or "Tecnología") for d in updated_list}
                    )
                if expired_asins:
                    telegram_delivery_status["pruned_expired_asins"] = sorted(expired_asins)
                meta = preserved.setdefault("metadata", {})
                if isinstance(meta, dict):
                    meta["last_live_check_at"] = run_now_iso
                    meta["telegram_delivery_status"] = telegram_delivery_status
                    meta["audit_report"] = audit_report
                    if isinstance(preserved.get("deals"), list):
                        meta["active_deals_count"] = len(preserved["deals"])
                deals_json_path.write_text(
                    json.dumps(preserved, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
        except Exception:
            pass
        exported_path = str(deals_json_path)
    else:
        db.clear_stale_published_deals([d["asin"] for d in approved_deals])
        exported_path = db.export_deals_json(
            output_path=str(deals_json_path),
            metadata={
                "trm_cop": active_trm,
                "associate_tag": ASSOCIATE_TAG,
                "public_web_url": PUBLIC_WEB_URL,
                "zero_token_mode": True,
                "monitored_products_count": len(catalog),
                "active_deals_count": len(approved_deals),
                "new_price_drops_count": new_price_drops_count,
                "telegram_delivery_status": telegram_delivery_status,
                "audit_report": audit_report,
            },
        )

    return {
        "status": "ok",
        "zero_token_llm_tokens_used": 0,
        "trm_cop": active_trm,
        "monitored_count": len(catalog),
        "approved_deals_count": len(approved_deals),
        "new_price_drops_count": new_price_drops_count,
        "telegram_delivery_status": telegram_delivery_status,
        "audit_report": audit_report,
        "exported_json": exported_path,
        "deals": approved_deals,
        "broadcasts": broadcast_results,
    }


@app.on_event("startup")
def startup_seed() -> None:
    """Ensure SQLite and public/data/deals.json are populated on startup."""
    deals_json = DATA_DIR / "deals.json"
    if not deals_json.exists():
        run_zero_token_pipeline()


@app.get("/api/health")
def api_health() -> dict:
    return {
        "status": "healthy",
        "service": "amazon-colombia-affiliates",
        "zero_token_polling": True,
        "public_web_url": PUBLIC_WEB_URL,
        "associate_tag": ASSOCIATE_TAG,
    }


@app.get("/api/trm")
def api_trm() -> dict:
    trm = fetch_live_trm_cop(default_trm=DEFAULT_TRM_COP)
    return {"trm_cop": trm, "currency_pair": "USD/COP"}


@app.get("/api/deals")
def api_get_deals(
    category: Optional[str] = Query(default=None),
    tax_free_only: bool = Query(default=False),
    free_shipping_only: bool = Query(default=False),
    min_discount: float = Query(default=0.0),
    search: Optional[str] = Query(default=None),
) -> dict:
    db = Database(db_path=DB_PATH)
    db.init_db()
    deals = db.get_published_deals(
        category=category,
        tax_free_only=tax_free_only,
        free_shipping_only=free_shipping_only,
        min_discount=min_discount,
        search=search,
    )
    if not deals and not any([category, tax_free_only, free_shipping_only, min_discount, search]):
        pipeline_res = run_zero_token_pipeline()
        deals = pipeline_res["deals"]

    return {
        "status": "ok",
        "count": len(deals),
        "trm_cop": DEFAULT_TRM_COP,
        "associate_tag": ASSOCIATE_TAG,
        "public_web_url": PUBLIC_WEB_URL,
        "deals": deals,
    }


@app.post("/api/scan")
def api_trigger_scan(trm_cop: Optional[float] = Query(default=None)) -> dict:
    """Manually triggers a Zero-Token scan cycle and refreshes Telegram, Teams, and Web cards."""
    result = run_zero_token_pipeline(trm_cop=trm_cop)
    return {
        "status": "ok",
        "message": "Barrido Zero-Token completado (0 tokens LLM consumidos)",
        "trm_cop": result["trm_cop"],
        "monitored_count": result["monitored_count"],
        "approved_deals_count": result["approved_deals_count"],
        "deals": result["deals"],
    }


@app.get("/api/previews")
def api_get_channel_previews() -> dict:
    """Returns the generated Telegram & Microsoft Teams cards from the outbox."""
    broadcaster = ChannelBroadcaster(outbox_path=str(DATA_DIR / "outbox_cards.json"))
    cards = broadcaster.get_outbox_cards()
    if not cards:
        run_zero_token_pipeline()
        cards = broadcaster.get_outbox_cards()
    return {
        "status": "ok",
        "count": len(cards),
        "cards": cards,
    }


# Serve static files from public/ when running via Uvicorn locally
if PUBLIC_DIR.exists():
    @app.get("/")
    def serve_index():
        index_file = PUBLIC_DIR / "index.html"
        if not index_file.exists():
            raise HTTPException(status_code=404, detail="index.html not found")
        return FileResponse(index_file)

    @app.get("/deal/{asin}")
    def serve_deal_deep_link(asin: str):
        index_file = PUBLIC_DIR / "index.html"
        if not index_file.exists():
            raise HTTPException(status_code=404, detail="index.html not found")
        return FileResponse(index_file)

    app.mount("/", StaticFiles(directory=str(PUBLIC_DIR), html=True), name="public")
