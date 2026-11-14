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
    build_teams_adaptive_card,
    build_telegram_card,
    build_vercel_deal_url,
)
from src.db.database import Database
from src.evaluator.colombia_rules import evaluate_colombia_deal, fetch_live_trm_cop
from src.monitor.amazon_scraper import AmazonMonitorScraper
from src.monitor.price_watcher import detect_price_drop

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PUBLIC_DIR = PROJECT_ROOT / "public"
DATA_DIR = PUBLIC_DIR / "data"
DB_PATH = str(PROJECT_ROOT / "data" / "deals.db")

ASSOCIATE_TAG = os.getenv("AMAZON_ASSOCIATE_TAG", "pillepues-20")
PUBLIC_WEB_URL = os.getenv("PUBLIC_WEB_URL", "https://vitrina-colombia-ofertas.vercel.app")
DEFAULT_TRM_COP = float(os.getenv("DEFAULT_TRM_COP", "4150.0"))
MIN_DISCOUNT_PCT = float(os.getenv("MIN_DISCOUNT_PERCENT", "20.0"))

app = FastAPI(
    title="Amazon Colombia Deals & Zero-Token Agentic Tracker",
    description="API Serverless para monitoreo Zero-Token de Amazon.com hacia Colombia (Telegram, Microsoft Teams y Web en Vercel)",
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
    broadcaster = ChannelBroadcaster(
        outbox_path=str(DATA_DIR / "outbox_cards.json"),
    )

    catalog = scraper.fetch_catalog(use_seed=True)
    approved_deals: list[dict] = []
    broadcast_results: list[dict] = []

    for raw_item in catalog:
        db.upsert_product(raw_item)
        db.record_price(
            asin=raw_item["asin"],
            price_usd=float(raw_item["price_usd"]),
            list_price_usd=float(raw_item.get("list_price_usd", raw_item["price_usd"])),
            avg_90d_usd=float(raw_item.get("avg_90d_usd", raw_item["price_usd"])),
        )

        # Layer 0: Deterministic Zero-Token Price Drop Check
        drop_info = detect_price_drop(
            current_price=float(raw_item["price_usd"]),
            avg_90d=float(raw_item.get("avg_90d_usd", 0.0)),
            list_price=float(raw_item.get("list_price_usd", 0.0)),
            min_discount_pct=MIN_DISCOUNT_PCT,
        )
        if not drop_info["is_deal"]:
            continue

        # Layer 1: Colombia Customs & TRM Evaluation (arancel-guardian-analista)
        evaluated = evaluate_colombia_deal(
            product=raw_item,
            trm_cop=active_trm,
            min_discount_pct=MIN_DISCOUNT_PCT,
        )
        if not evaluated.get("approved_for_colombia", False):
            continue

        # Layer 2: Affiliate Links & Copy Generation (midas-copy-afiliados)
        asin = evaluated["asin"]
        evaluated["affiliate_url"] = build_affiliate_url(asin, associate_tag=ASSOCIATE_TAG)
        evaluated["web_url"] = build_vercel_deal_url(asin, public_web_url=PUBLIC_WEB_URL)

        tg_card = build_telegram_card(
            deal=evaluated,
            associate_tag=ASSOCIATE_TAG,
            public_web_url=PUBLIC_WEB_URL,
        )
        teams_card = build_teams_adaptive_card(
            deal=evaluated,
            associate_tag=ASSOCIATE_TAG,
            public_web_url=PUBLIC_WEB_URL,
        )

        # Save in SQLite & broadcast to Telegram + Teams (heraldo-difusor-canales)
        db.save_published_deal(evaluated)
        b_res = broadcaster.broadcast_deal(
            deal=evaluated,
            telegram_card=tg_card,
            teams_card=teams_card,
        )
        approved_deals.append(evaluated)
        broadcast_results.append(b_res)

    # Layer 3: Export static JSON catalog for Vercel CDN (vitrina-web-publisher)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    exported_path = db.export_deals_json(
        output_path=str(DATA_DIR / "deals.json"),
        metadata={
            "trm_cop": active_trm,
            "associate_tag": ASSOCIATE_TAG,
            "public_web_url": PUBLIC_WEB_URL,
            "zero_token_mode": True,
            "monitored_products_count": len(catalog),
            "active_deals_count": len(approved_deals),
        },
    )

    return {
        "status": "ok",
        "zero_token_llm_tokens_used": 0,
        "trm_cop": active_trm,
        "monitored_count": len(catalog),
        "approved_deals_count": len(approved_deals),
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
