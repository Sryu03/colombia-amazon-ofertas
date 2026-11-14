"""FastAPI Serverless Orchestrator & Local Server for Amazon Colombia Affiliates (Vercel-ready)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

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
    discover_trending_asins,
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


def run_zero_token_pipeline(trm_cop: Optional[float] = None) -> dict:
    """Runs the complete deterministic Zero-Token monitoring, evaluation, copywriting, broadcasting, and web export pipeline."""
    db = Database(db_path=DB_PATH)
    db.init_db()

    active_trm = trm_cop or fetch_live_trm_cop(default_trm=DEFAULT_TRM_COP)
    scraper = AmazonMonitorScraper()
    price_history = PriceHistoryStore(path=PRICE_HISTORY_PATH)
    broadcaster = ChannelBroadcaster(
        outbox_path=str(DATA_DIR / "outbox_cards.json"),
    )

    watchlist_items = load_watchlist_asins(WATCHLIST_PATH)
    if LIVE_SCRAPE and DISCOVERY_ENABLED:
        existing_asins = {str(item.get("asin", "")).upper() for item in watchlist_items}
        newly_discovered = discover_trending_asins(
            existing_asins=existing_asins,
            max_new_asins=30,
        )
        if newly_discovered:
            watchlist_items = (newly_discovered + watchlist_items)[:150]
            save_watchlist_asins(WATCHLIST_PATH, watchlist_items)

    catalog = scraper.fetch_catalog(
        use_seed=not LIVE_SCRAPE,
        extra_items=watchlist_items,
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
        )
        if not evaluated.get("approved_for_colombia", False):
            continue

        # Strict coherence, Colombia shipping & image gate
        ships_to_colombia = bool(evaluated.get("ships_to_colombia", False)) and not bool(
            evaluated.get("requires_locker", False)
        )
        has_https_image = str(evaluated.get("image_url") or "").strip().lower().startswith("https://")
        has_valid_title = not str(evaluated.get("title") or "").strip().lower().startswith("amazon product")
        has_coherent_price = (
            evaluated.get("price_usd", 0.0) > 0.0
            and evaluated.get("reference_price_usd", 0.0) > evaluated.get("price_usd", 0.0)
            and evaluated.get("savings_usd", 0.0) >= 1.0
        )
        if not (ships_to_colombia and has_coherent_price and has_valid_title and has_https_image):
            continue

        # Layer 2: Affiliate Links & Copy Generation (midas-copy-afiliados)
        evaluated["affiliate_url"] = build_affiliate_url(asin, associate_tag=ASSOCIATE_TAG)
        evaluated["web_url"] = build_vercel_deal_url(asin, public_web_url=PUBLIC_WEB_URL)
        evaluated["is_new_price_drop"] = history_event["is_new_drop"]
        evaluated["previous_price_usd"] = history_event["previous_price_usd"]

        tg_card = build_telegram_card(
            deal=evaluated,
            associate_tag=ASSOCIATE_TAG,
            public_web_url=PUBLIC_WEB_URL,
        )
        evaluated["telegram_copy"] = tg_card["caption_html"]
        approved_candidates.append((evaluated, tg_card, history_event))

    # Priorizar estrictamente por mejor oferta/descuento y envío a Colombia (NO por comisión)
    approved_candidates.sort(key=lambda item: deal_priority_key(item[0]), reverse=True)
    approved_deals: list[dict] = []
    live_sent_count = 0

    for evaluated, tg_card, history_event in approved_candidates:
        asin = evaluated["asin"]
        price_usd = evaluated["price_usd"]

        db.save_published_deal(evaluated)
        approved_deals.append(evaluated)

        should_send_live = (
            (history_event["is_new_drop"] and live_sent_count < MAX_TELEGRAM_PER_CYCLE)
            or not LIVE_SCRAPE
        )
        if should_send_live:
            b_res = broadcaster.broadcast_deal(
                deal=evaluated,
                telegram_card=tg_card,
            )
            broadcast_results.append(b_res)
            if history_event["is_new_drop"]:
                new_price_drops_count += 1
                live_sent_count += 1
                if broadcaster.telegram_bot_token:
                    price_history.mark_published(asin, price_usd)

    # Layer 3: Export static JSON catalog & price history for Vercel CDN
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    price_history.save()

    deals_json_path = DATA_DIR / "deals.json"
    if LIVE_SCRAPE and len(catalog) == 0 and deals_json_path.exists():
        # Preserve existing public catalog if a single live scrape cycle got temporarily blocked
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
            },
        )

    return {
        "status": "ok",
        "zero_token_llm_tokens_used": 0,
        "trm_cop": active_trm,
        "monitored_count": len(catalog),
        "approved_deals_count": len(approved_deals),
        "new_price_drops_count": new_price_drops_count,
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
