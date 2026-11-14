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
            "asin": "B0B9C4DKKG",
            "title": "SAMSUNG 990 PRO SSD 2TB PCIe 4.0 M.2",
            "price_usd": 149.99,
            "list_price_usd": 249.99,
            "avg_90d_usd": 199.99,
            "ships_to_colombia": True,
            "free_shipping_co": True,
            "shipping_cost_usd": 0.0,
            "requires_locker": False,
        }
        eval_ssd = evaluate_colombia_deal(ssd, trm_cop=4150.0)
        self.assertTrue(eval_ssd["tax_free_colombia"])
        self.assertEqual(eval_ssd["estimated_import_tax_usd"], 0.0)
        self.assertIn("Sin Impuestos DIAN", eval_ssd["tax_badge_co"])
        self.assertIn("Envío GRATIS directo a Colombia", eval_ssd["shipping_badge_co"])
        self.assertFalse(eval_ssd["requires_locker"])
        self.assertTrue(eval_ssd["cheaper_than_before"])
        self.assertIn("Necesita casillero: No", eval_ssd["locker_badge_co"])
        self.assertTrue(eval_ssd["approved_for_colombia"])
        self.assertIn("COP", format_cop(eval_ssd["price_cop"]))

        # Product requiring Miami locker
        minipc = {
            "asin": "B0BP9MDCQZ",
            "title": "Amazon Fire TV Stick 4K (Requiere casillero)",
            "price_usd": 29.99,
            "list_price_usd": 49.99,
            "avg_90d_usd": 44.99,
            "ships_to_colombia": False,
            "free_shipping_co": False,
            "shipping_cost_usd": 12.0,
            "requires_locker": True,
        }
        eval_locker = evaluate_colombia_deal(minipc, trm_cop=4150.0)
        self.assertTrue(eval_locker["tax_free_colombia"])
        self.assertTrue(eval_locker["requires_locker"])
        self.assertEqual(eval_locker["shipping_cost_usd"], 12.0)
        self.assertIn("Necesita casillero: Sí", eval_locker["locker_badge_co"])

    def test_affiliate_builder_and_cards(self):
        dirty_url = "https://www.amazon.com/Samsung-990-PRO-2TB/dp/B0B9C4DKKG/ref=sr_1_1?crid=123&qid=456"
        asin = extract_asin(dirty_url)
        self.assertEqual(asin, "B0B9C4DKKG")

        aff_url = build_affiliate_url(dirty_url, associate_tag="pillepues-20")
        self.assertEqual(
            aff_url,
            "https://www.amazon.com/dp/B0B9C4DKKG?linkCode=ll1&tag=pillepues-20&language=es_US&ref_=as_li_ss_tl",
        )

        vercel_url = build_vercel_deal_url(asin, public_web_url="https://vitrina-colombia-ofertas.vercel.app")
        self.assertEqual(vercel_url, "https://vitrina-colombia-ofertas.vercel.app/?asin=B0B9C4DKKG")

        deal = evaluate_colombia_deal(
            {
                "asin": "B0B9C4DKKG",
                "title": "SAMSUNG 990 PRO SSD 2TB PCIe 4.0 M.2",
                "price_usd": 149.99,
                "list_price_usd": 249.99,
                "avg_90d_usd": 199.99,
                "ships_to_colombia": True,
                "free_shipping_co": True,
                "shipping_cost_usd": 0.0,
                "requires_locker": False,
                "highlights": ["Lectura hasta 7450 MB/s", "Compatible con PS5 y PC"],
            },
            trm_cop=4150.0,
        )
        tg_card = build_telegram_card(deal, associate_tag="pillepues-20")
        self.assertLessEqual(len(tg_card["caption_html"]), 1024)
        self.assertEqual(len(tg_card["reply_markup"]["inline_keyboard"]), 2)
        self.assertIn("linkCode=ll1", tg_card["reply_markup"]["inline_keyboard"][0][0]["url"])
        self.assertIn("ref_=as_li_ss_tl", tg_card["reply_markup"]["inline_keyboard"][0][0]["url"])
        self.assertIn("Más barato que antes", tg_card["caption_html"])
        self.assertIn("Necesita casillero:", tg_card["caption_html"])


    def test_full_pipeline_and_vercel_bundle(self):
        res = run_zero_token_pipeline(trm_cop=4150.0)
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["zero_token_llm_tokens_used"], 0)
        self.assertGreaterEqual(res["approved_deals_count"], 10)

        project_dir = Path(__file__).resolve().parent.parent
        deals_json_path = project_dir / "public" / "data" / "deals.json"
        outbox_json_path = project_dir / "public" / "data" / "outbox_cards.json"

        self.assertTrue(deals_json_path.exists())
        self.assertTrue(outbox_json_path.exists())

        vercel_check = deploy_to_vercel(str(project_dir))
        self.assertIn(vercel_check["status"], ("ready_for_vercel", "bundle_ready", "deployed", "hook_triggered"))

    def test_discovery_and_price_history(self):
        from src.monitor.discovery import extract_asins_from_listing_html
        from src.monitor.price_history import PriceHistoryStore

        sample_html = (
            '<a href="/Some-Product/dp/B0B9C4DKKG/ref=zg_bs">Item 1</a>'
            '<a href="/Another-Product/dp/B0863FR3S9?th=1">Item 2</a>'
            '<a href="/Some-Product/dp/B0B9C4DKKG">Duplicate</a>'
        )
        asins = extract_asins_from_listing_html(sample_html)
        self.assertEqual(asins, ["B0B9C4DKKG", "B0863FR3S9"])

        with tempfile.TemporaryDirectory() as tmpdir:
            store = PriceHistoryStore(path=Path(tmpdir) / "price_history.json")
            first = store.evaluate_and_record("B0B9C4DKKG", current_price_usd=149.99, avg_90d_usd=199.99)
            self.assertTrue(first["is_new_drop"])
            store.mark_published("B0B9C4DKKG", 149.99)

            same_price = store.evaluate_and_record("B0B9C4DKKG", current_price_usd=149.99, avg_90d_usd=199.99)
            self.assertFalse(same_price["is_new_drop"])

            cheaper = store.evaluate_and_record("B0B9C4DKKG", current_price_usd=139.99, avg_90d_usd=199.99)
            self.assertTrue(cheaper["is_new_drop"])
            store.save()
            self.assertTrue((Path(tmpdir) / "price_history.json").exists())

    def test_seed_catalog_has_only_real_https_images_and_coherent_prices(self):
        from src.monitor.amazon_scraper import SEED_PRODUCTS_COLOMBIA

        self.assertGreaterEqual(len(SEED_PRODUCTS_COLOMBIA), 18)
        seen_asins = set()
        for item in SEED_PRODUCTS_COLOMBIA:
            asin = item["asin"]
            self.assertRegex(asin, r"^[A-Z0-9]{10}$")
            self.assertNotIn(asin, seen_asins)
            seen_asins.add(asin)

            img = item.get("image_url", "")
            self.assertTrue(img.startswith("https://"), f"{asin} missing https image_url: {img}")
            self.assertFalse(img.startswith("data:"), f"{asin} must not use SVG data URI")
            self.assertGreater(item["list_price_usd"], item["price_usd"])
            self.assertGreater(item["avg_90d_usd"], item["price_usd"])

    def test_live_mode_never_falls_back_to_seed_prices(self):
        from unittest.mock import patch

        scraper = AmazonMonitorScraper()
        with patch.object(scraper, "fetch_asin_live", return_value=None):
            live_catalog = scraper.fetch_catalog(use_seed=False, max_live_asins=5)
            self.assertEqual(live_catalog, [])

    def test_parse_amazon_html_extracts_photo_and_rejects_incoherent_discount(self):
        from src.monitor.amazon_scraper import parse_amazon_html

        captcha_html = "<html><body>Sorry, we just need to make sure you're not a robot. Type the characters you see in this image.</body></html>"
        captcha_parsed = parse_amazon_html(captcha_html, "B09X1H88VP")
        self.assertFalse(captcha_parsed["live_verified"])
        self.assertEqual(captcha_parsed["price_usd"], 0.0)

        no_discount_html = """
        <html>
          <head><meta property="og:image" content="https://m.media-amazon.com/images/I/test._AC_SL1500_.jpg"/></head>
          <body>
            <span id="productTitle">UGREEN Nexode 65W Charger</span>
            <div id="corePriceDisplay_desktop_feature_div">
              <span class="a-price priceToPay"><span class="a-offscreen">$24.99</span></span>
            </div>
          </body>
        </html>
        """
        parsed_no_disc = parse_amazon_html(no_discount_html, "B09X1H88VP")
        self.assertTrue(parsed_no_disc["live_verified"])
        self.assertEqual(parsed_no_disc["price_usd"], 24.99)
        self.assertEqual(parsed_no_disc["list_price_usd"], 24.99)
        self.assertEqual(parsed_no_disc["image_url"], "https://m.media-amazon.com/images/I/test._AC_SL1500_.jpg")

        drop = detect_price_drop(
            current_price=parsed_no_disc["price_usd"],
            avg_90d=parsed_no_disc["avg_90d_usd"],
            list_price=parsed_no_disc["list_price_usd"],
        )
        self.assertFalse(drop["is_deal"])

        eval_no_disc = evaluate_colombia_deal(parsed_no_disc)
        self.assertFalse(eval_no_disc["approved_for_colombia"])

    def test_telegram_sendphoto_and_html_escaping_and_price_coherence(self):
        deal = evaluate_colombia_deal(
            {
                "asin": "B0B9C4DKKG",
                "title": "Samsung 990 PRO <2TB> & NVMe SSD",
                "price_usd": 149.99,
                "list_price_usd": 249.99,
                "avg_90d_usd": 189.99,
                "ships_to_colombia": True,
                "free_shipping_co": True,
                "shipping_cost_usd": 0.0,
                "requires_locker": False,
                "image_url": "https://m.media-amazon.com/images/I/71K6m2A+WJL._AC_SL1500_.jpg",
            },
            trm_cop=4150.0,
        )
        card = build_telegram_card(deal, associate_tag="pillepues-20")
        self.assertIn("&lt;2TB&gt; &amp; NVMe", card["caption_html"])
        self.assertIn("<s>$189.99 USD</s>", card["caption_html"])
        self.assertIn("Ahorras $40.00 USD", card["caption_html"])
        self.assertIn("B0B9C4DKKG", card["reply_markup"]["inline_keyboard"][0][0]["url"])

        broadcaster = ChannelBroadcaster(telegram_bot_token="")
        tg_res = broadcaster.send_telegram(card)
        self.assertEqual(tg_res["api_method"], "sendPhoto")
        self.assertTrue(tg_res["payload"]["photo"].startswith("https://"))


if __name__ == "__main__":
    unittest.main()
