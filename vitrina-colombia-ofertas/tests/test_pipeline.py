"""End-to-end automated test suite for the Amazon Colombia Affiliates Agentic System."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from api.index import run_zero_token_pipeline
from src.broadcaster.channels import ChannelBroadcaster
from src.copywriter.affiliate_builder import (
    build_affiliate_url,
    build_teams_adaptive_card,
    build_telegram_card,
    build_vercel_deal_url,
    extract_asin,
)
from src.db.database import Database
from src.evaluator.colombia_rules import evaluate_colombia_deal, format_cop
from src.monitor.amazon_scraper import AmazonMonitorScraper
from src.monitor.price_watcher import detect_price_drop
from src.publisher.vercel_deployer import deploy_to_vercel


class TestAmazonColombiaPipeline(unittest.TestCase):
    def test_zero_token_price_watcher(self):
        # Real 40% drop below 90-day average
        res = detect_price_drop(current_price=119.99, avg_90d=199.99, list_price=229.99, min_discount_pct=20.0)
        self.assertTrue(res["is_deal"])
        self.assertGreaterEqual(res["discount_pct"], 35.0)
        self.assertTrue(res["is_historic_low"])

        # Fake discount: list_price inflated ($250), but avg_90d is $125 and current is $119
        fake = detect_price_drop(current_price=119.0, avg_90d=125.0, list_price=250.0, min_discount_pct=20.0)
        self.assertFalse(fake["is_deal"])

    def test_colombia_customs_rules(self):
        # Product <= $200 USD and >= $35 USD: Tax-free DIAN & direct free shipping to CO
        ssd = {
            "asin": "B0BHJJ9Y77",
            "title": "Samsung 990 PRO SSD 2TB PCIe 4.0 M.2",
            "price_usd": 119.99,
            "list_price_usd": 209.99,
            "avg_90d_usd": 189.99,
            "ships_to_colombia": True,
            "free_shipping_co": True,
        }
        eval_ssd = evaluate_colombia_deal(ssd, trm_cop=4150.0)
        self.assertTrue(eval_ssd["tax_free_colombia"])
        self.assertEqual(eval_ssd["estimated_import_tax_usd"], 0.0)
        self.assertIn("Sin Impuestos DIAN", eval_ssd["tax_badge_co"])
        self.assertIn("Envío GRATIS directo a Colombia", eval_ssd["shipping_badge_co"])
        self.assertTrue(eval_ssd["approved_for_colombia"])
        self.assertIn("COP", format_cop(eval_ssd["price_cop"]))

        # Product > $200 USD: Pays 19% Colombia import IVA
        minipc = {
            "asin": "B0C9J6P7XM",
            "title": "Beelink SER6 Mini PC Ryzen 9",
            "price_usd": 249.00,
            "list_price_usd": 399.00,
            "avg_90d_usd": 359.00,
            "ships_to_colombia": True,
            "free_shipping_co": True,
        }
        eval_pc = evaluate_colombia_deal(minipc, trm_cop=4150.0)
        self.assertFalse(eval_pc["tax_free_colombia"])
        self.assertGreater(eval_pc["estimated_import_tax_usd"], 0.0)

    def test_affiliate_builder_and_cards(self):
        dirty_url = "https://www.amazon.com/Samsung-990-PRO-2TB/dp/B0BHJJ9Y77/ref=sr_1_1?crid=123&qid=456"
        asin = extract_asin(dirty_url)
        self.assertEqual(asin, "B0BHJJ9Y77")

        aff_url = build_affiliate_url(dirty_url, associate_tag="mi-tag-co-20")
        self.assertEqual(aff_url, "https://www.amazon.com/dp/B0BHJJ9Y77?tag=mi-tag-co-20&language=es_US")

        vercel_url = build_vercel_deal_url(asin, public_web_url="https://vitrina-colombia-ofertas.vercel.app")
        self.assertEqual(vercel_url, "https://vitrina-colombia-ofertas.vercel.app/?asin=B0BHJJ9Y77")

        deal = evaluate_colombia_deal(
            {
                "asin": "B0BHJJ9Y77",
                "title": "Samsung 990 PRO SSD 2TB PCIe 4.0 M.2",
                "price_usd": 119.99,
                "list_price_usd": 209.99,
                "avg_90d_usd": 189.99,
                "ships_to_colombia": True,
                "free_shipping_co": True,
                "highlights": ["Lectura hasta 7450 MB/s", "Compatible con PS5 y PC"],
            },
            trm_cop=4150.0,
        )
        tg_card = build_telegram_card(deal, associate_tag="mi-tag-co-20")
        self.assertLessEqual(len(tg_card["caption_html"]), 1024)
        self.assertEqual(len(tg_card["reply_markup"]["inline_keyboard"]), 2)

        teams_card = build_teams_adaptive_card(deal, associate_tag="mi-tag-co-20")
        self.assertEqual(teams_card["type"], "message")
        self.assertEqual(teams_card["attachments"][0]["content"]["type"], "AdaptiveCard")

    def test_full_pipeline_and_vercel_bundle(self):
        res = run_zero_token_pipeline(trm_cop=4150.0)
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["zero_token_llm_tokens_used"], 0)
        self.assertGreaterEqual(res["approved_deals_count"], 10)

        project_dir = Path("/home/antigravity/amazon-colombia-affiliates")
        deals_json_path = project_dir / "public" / "data" / "deals.json"
        outbox_json_path = project_dir / "public" / "data" / "outbox_cards.json"

        self.assertTrue(deals_json_path.exists())
        self.assertTrue(outbox_json_path.exists())

        vercel_check = deploy_to_vercel(str(project_dir))
        self.assertIn(vercel_check["status"], ("ready_for_vercel", "bundle_ready", "deployed", "hook_triggered"))


if __name__ == "__main__":
    unittest.main()
