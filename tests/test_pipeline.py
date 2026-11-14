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
        self.assertFalse(eval_locker["approved_for_colombia"])
        self.assertIn("SIN ENVÍO A COLOMBIA", eval_locker["deal_tier"])

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
        self.assertTrue(all(d.get("ships_to_colombia") and not d.get("requires_locker") for d in res["deals"]))
        discounts_without_drop_tier = [d["discount_pct"] for d in res["deals"] if not d.get("is_new_price_drop")]
        self.assertEqual(discounts_without_drop_tier, sorted(discounts_without_drop_tier, reverse=True))

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
            '<div data-asin="B0CHWRXH8B">Deal 1</div>'
            '<a href="/Some-Product/dp/B0B9C4DKKG/ref=zg_bs">Item 1</a>'
            '<a href="/Another-Product/dp/B0863FR3S9?th=1">Item 2</a>'
            '<script>{"asin":"B07GBZ4Q68"}</script>'
            '<a href="/Some-Product/dp/B0B9C4DKKG">Duplicate</a>'
        )
        asins = extract_asins_from_listing_html(sample_html)
        self.assertEqual(asins, ["B0CHWRXH8B", "B0B9C4DKKG", "B0863FR3S9", "B07GBZ4Q68"])

        from src.monitor.discovery import parse_search_deals_html

        deals_search_html = """
        <html><body>
          <div data-asin="B0B9C4DKKG" data-component-type="s-search-result">
            <h2><span>Samsung 990 PRO SSD 2TB PCIe 4.0</span></h2>
            <img class="s-image" src="https://m.media-amazon.com/images/I/71K6m2A+WJL._AC_UL320_.jpg"/>
            <span class="a-price"><span class="a-offscreen">$149.99</span></span>
            <span class="a-price a-text-price"><span class="a-offscreen">$249.99</span></span>
            <span>FREE delivery to Colombia</span>
          </div>
          <div data-asin="B09B8V1LZ3" data-component-type="s-search-result">
            <h2><span>Echo Dot 5th Gen</span></h2>
            <img class="s-image" src="https://m.media-amazon.com/images/I/echo._AC_UL320_.jpg"/>
            <span class="a-price"><span class="a-offscreen">$29.99</span></span>
            <span class="a-price a-text-price"><span class="a-offscreen">$49.99</span></span>
            <span>This item cannot be shipped to your selected delivery location</span>
          </div>
        </body></html>
        """
        parsed_deals = parse_search_deals_html(deals_search_html, category="Tecnología")
        self.assertEqual(len(parsed_deals), 1)
        self.assertEqual(parsed_deals[0]["asin"], "B0B9C4DKKG")
        self.assertEqual(parsed_deals[0]["price_usd"], 149.99)
        self.assertEqual(parsed_deals[0]["list_price_usd"], 249.99)
        self.assertTrue(parsed_deals[0]["ships_to_colombia"])
        self.assertTrue(parsed_deals[0]["free_shipping_co"])

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

    def test_parse_bestsellers_deals_and_token_sanitization(self):
        from src.broadcaster.channels import _sanitize_error_detail
        from src.monitor.discovery import parse_bestsellers_deals_html

        raw_err = "Client error '400 Bad Request' for url 'https://api.telegram.org/bot123456:ABCdef-XYZ_987/sendPhoto'"
        sanitized = _sanitize_error_detail(raw_err, token="123456:ABCdef-XYZ_987")
        self.assertNotIn("ABCdef-XYZ_987", sanitized)
        self.assertIn("bot<REDACTED>", sanitized)

        bs_html = """
        <html><body>
          <div id="gridItemRoot" data-asin="B09B8V1LZ3">
            <img src="https://m.media-amazon.com/images/I/echo._AC_UL320_.jpg" alt="Echo Dot 5th Gen Smart Speaker" />
            <span class="p13n-sc-price">$29.99</span>
            <span class="a-price a-text-price"><span class="a-offscreen">$49.99</span></span>
            <span>Ships to Colombia</span>
          </div>
          <div id="gridItemRoot" data-asin="B07GBZ4Q68">
            <img src="https://m.media-amazon.com/images/I/61mpMH5TzkL._AC_SL1500_.jpg" alt="Logitech G502 HERO High Performance Gaming Mouse" />
            <span class="p13n-sc-price">$34.99</span>
            <span class="a-price a-text-price"><span class="a-offscreen">$79.99</span></span>
            <span>FREE delivery to Colombia</span>
          </div>
        </body></html>
        """
        bs_deals = parse_bestsellers_deals_html(bs_html, category="Gaming")
        self.assertEqual(len(bs_deals), 1)
        self.assertEqual(bs_deals[0]["asin"], "B07GBZ4Q68")
        self.assertEqual(bs_deals[0]["price_usd"], 34.99)
        self.assertEqual(bs_deals[0]["list_price_usd"], 79.99)

    def test_publish_verified_catalog_fallback_when_live_scrape_empty(self):
        from datetime import datetime, timezone
        from unittest.mock import patch
        import api.index as idx_mod

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            public_dir = tmp_path / "public"
            data_dir = public_dir / "data"
            data_dir.mkdir(parents=True, exist_ok=True)

            sample_deals = {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "total_deals": 2,
                "deals": [
                    {
                        "asin": "B07J2Z5DBM",
                        "title": "TOZO T10 Audifonos Bluetooth",
                        "category": "Audio",
                        "price_usd": 18.99,
                        "list_price_usd": 39.99,
                        "avg_90d_usd": 29.99,
                        "reference_price_usd": 29.99,
                        "discount_pct": 36.7,
                        "savings_usd": 11.0,
                        "ships_to_colombia": True,
                        "free_shipping_co": False,
                        "requires_locker": False,
                        "image_url": "https://m.media-amazon.com/images/I/tozo.jpg",
                        "affiliate_url": "https://www.amazon.com/dp/B07J2Z5DBM?linkCode=ll1&tag=pillepues-20&language=es_US&ref_=as_li_ss_tl",
                    },
                    {
                        "asin": "B09X1H88VP",
                        "title": "UGREEN Nexode 65W Cargador GaN",
                        "category": "Tecnología",
                        "price_usd": 29.99,
                        "list_price_usd": 49.99,
                        "avg_90d_usd": 42.99,
                        "reference_price_usd": 42.99,
                        "discount_pct": 30.2,
                        "savings_usd": 13.0,
                        "ships_to_colombia": True,
                        "free_shipping_co": False,
                        "requires_locker": False,
                        "image_url": "https://m.media-amazon.com/images/I/ugreen.jpg",
                        "affiliate_url": "https://www.amazon.com/dp/B09X1H88VP?linkCode=ll1&tag=pillepues-20&language=es_US&ref_=as_li_ss_tl",
                    },
                ],
            }
            deals_file = data_dir / "deals.json"
            deals_file.write_text(json.dumps(sample_deals), encoding="utf-8")

            fake_broadcaster = ChannelBroadcaster(
                telegram_bot_token="fake-token",
                telegram_chat_id="@pillepues",
                outbox_path=str(data_dir / "outbox_cards.json"),
            )

            with (
                patch.object(idx_mod, "DATA_DIR", data_dir),
                patch.object(idx_mod, "DB_PATH", str(tmp_path / "deals.db")),
                patch.object(idx_mod, "WATCHLIST_PATH", tmp_path / "watchlist.json"),
                patch.object(idx_mod, "PRICE_HISTORY_PATH", data_dir / "price_history.json"),
                patch.object(idx_mod, "LIVE_SCRAPE", True),
                patch.object(idx_mod, "DISCOVERY_ENABLED", False),
                patch.object(AmazonMonitorScraper, "fetch_catalog", return_value=[]),
                patch.object(AmazonMonitorScraper, "fetch_asin_live", return_value=None),
                patch.object(
                    ChannelBroadcaster,
                    "_post_json",
                    return_value=(200, {"ok": True, "result": {"message_id": 101}}),
                ),
            ):
                res = idx_mod.run_zero_token_pipeline(
                    trm_cop=4150.0,
                    publish_verified_catalog=True,
                    max_telegram_per_cycle=2,
                    broadcaster=fake_broadcaster,
                )

            delivery = res["telegram_delivery_status"]
            self.assertEqual(delivery["source"], "verified_catalog")
            self.assertEqual(delivery["sent"], 2)
            self.assertEqual(delivery["sent_asins"], ["B07J2Z5DBM", "B09X1H88VP"])

            updated_deals = json.loads(deals_file.read_text(encoding="utf-8"))
            self.assertEqual(len(updated_deals["deals"]), 2)
            self.assertEqual(updated_deals["metadata"]["telegram_delivery_status"]["sent"], 2)

            history = json.loads((data_dir / "price_history.json").read_text(encoding="utf-8"))
            self.assertEqual(history["B07J2Z5DBM"]["last_published_price_usd"], 18.99)
            self.assertEqual(history["B09X1H88VP"]["last_published_price_usd"], 29.99)

    def test_stale_deals_blocked_and_live_reverify_prunes_expired(self):
        from datetime import datetime, timedelta, timezone
        from unittest.mock import patch
        import api.index as idx_mod
        from src.monitor.discovery import parse_search_deals_html

        # 1. Search parser must reject Prime-exclusive prices and Echo/Ring devices
        noisy_html = """
        <html><body>
          <div data-asin="B09B8V1LZ3" data-component-type="s-search-result">
            <h2><span>Echo Dot 5th Gen Smart Speaker</span></h2>
            <img class="s-image" src="https://m.media-amazon.com/images/I/echo._AC_UL320_.jpg"/>
            <span class="a-price"><span class="a-offscreen">$29.99</span></span>
            <span class="a-price a-text-price"><span class="a-offscreen">$49.99</span></span>
          </div>
          <div data-asin="B0B9C4DKKG" data-component-type="s-search-result">
            <h2><span>Samsung 990 PRO SSD 2TB</span></h2>
            <img class="s-image" src="https://m.media-amazon.com/images/I/ssd._AC_UL320_.jpg"/>
            <span class="a-price"><span class="a-offscreen">$139.99</span></span>
            <span class="a-price a-text-price"><span class="a-offscreen">$249.99</span></span>
            <span>With Prime</span>
          </div>
        </body></html>
        """
        self.assertEqual(parse_search_deals_html(noisy_html), [])

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            data_dir = tmp_path / "public" / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            stale_ts = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()

            stale_payload = {
                "generated_at": stale_ts,
                "total_deals": 2,
                "deals": [
                    {
                        "asin": "B07J2Z5DBM",
                        "title": "TOZO T10 Audifonos Bluetooth",
                        "category": "Audio",
                        "price_usd": 18.99,
                        "list_price_usd": 39.99,
                        "avg_90d_usd": 29.99,
                        "reference_price_usd": 29.99,
                        "discount_pct": 36.7,
                        "savings_usd": 11.0,
                        "ships_to_colombia": True,
                        "free_shipping_co": False,
                        "requires_locker": False,
                        "image_url": "https://m.media-amazon.com/images/I/tozo.jpg",
                    },
                    {
                        "asin": "B09X1H88VP",
                        "title": "UGREEN Nexode 65W Cargador GaN",
                        "category": "Tecnología",
                        "price_usd": 29.99,
                        "list_price_usd": 49.99,
                        "avg_90d_usd": 42.99,
                        "reference_price_usd": 42.99,
                        "discount_pct": 30.2,
                        "savings_usd": 13.0,
                        "ships_to_colombia": True,
                        "free_shipping_co": False,
                        "requires_locker": False,
                        "image_url": "https://m.media-amazon.com/images/I/ugreen.jpg",
                    },
                ],
            }
            deals_file = data_dir / "deals.json"
            deals_file.write_text(json.dumps(stale_payload), encoding="utf-8")

            fake_broadcaster = ChannelBroadcaster(
                telegram_bot_token="fake-token",
                telegram_chat_id="@pillepues",
                outbox_path=str(data_dir / "outbox_cards.json"),
            )

            # 2. If catalog is >90m old and Amazon blocks live re-verification, send 0 stale deals
            with (
                patch.object(idx_mod, "DATA_DIR", data_dir),
                patch.object(idx_mod, "DB_PATH", str(tmp_path / "deals.db")),
                patch.object(idx_mod, "WATCHLIST_PATH", tmp_path / "watchlist.json"),
                patch.object(idx_mod, "PRICE_HISTORY_PATH", data_dir / "price_history.json"),
                patch.object(idx_mod, "LIVE_SCRAPE", True),
                patch.object(idx_mod, "DISCOVERY_ENABLED", False),
                patch.object(AmazonMonitorScraper, "fetch_catalog", return_value=[]),
                patch.object(AmazonMonitorScraper, "fetch_asin_live", return_value=None),
            ):
                blocked_res = idx_mod.run_zero_token_pipeline(
                    trm_cop=4150.0,
                    publish_verified_catalog=True,
                    max_telegram_per_cycle=5,
                    broadcaster=fake_broadcaster,
                )
            self.assertEqual(blocked_res["telegram_delivery_status"]["sent"], 0)
            self.assertEqual(blocked_res["telegram_delivery_status"]["source"], "stale_catalog_blocked_recheck")
            self.assertEqual(blocked_res["telegram_delivery_status"]["skipped_stale_unverified"], 2)

            # 3. If live re-check succeeds: expired deal (B07J2Z5DBM) is pruned, updated deal (B09X1H88VP) is refreshed & sent
            def fake_live_recheck(asin: str):
                if asin == "B07J2Z5DBM":
                    return {
                        "asin": "B07J2Z5DBM",
                        "title": "TOZO T10 Audifonos Bluetooth",
                        "price_usd": 29.99,
                        "list_price_usd": 29.99,
                        "avg_90d_usd": 29.99,
                        "ships_to_colombia": True,
                        "free_shipping_co": False,
                        "requires_locker": False,
                        "image_url": "https://m.media-amazon.com/images/I/tozo.jpg",
                        "live_verified": True,
                    }
                if asin == "B09X1H88VP":
                    return {
                        "asin": "B09X1H88VP",
                        "title": "UGREEN Nexode 65W Cargador GaN",
                        "price_usd": 27.99,
                        "list_price_usd": 49.99,
                        "avg_90d_usd": 42.99,
                        "ships_to_colombia": True,
                        "free_shipping_co": False,
                        "requires_locker": False,
                        "image_url": "https://m.media-amazon.com/images/I/ugreen.jpg",
                        "live_verified": True,
                    }
                return None

            with (
                patch.object(idx_mod, "DATA_DIR", data_dir),
                patch.object(idx_mod, "DB_PATH", str(tmp_path / "deals.db")),
                patch.object(idx_mod, "WATCHLIST_PATH", tmp_path / "watchlist.json"),
                patch.object(idx_mod, "PRICE_HISTORY_PATH", data_dir / "price_history.json"),
                patch.object(idx_mod, "LIVE_SCRAPE", True),
                patch.object(idx_mod, "DISCOVERY_ENABLED", False),
                patch.object(AmazonMonitorScraper, "fetch_catalog", return_value=[]),
                patch.object(AmazonMonitorScraper, "fetch_asin_live", side_effect=fake_live_recheck),
                patch.object(
                    ChannelBroadcaster,
                    "_post_json",
                    return_value=(200, {"ok": True, "result": {"message_id": 202}}),
                ),
            ):
                recheck_res = idx_mod.run_zero_token_pipeline(
                    trm_cop=4150.0,
                    publish_verified_catalog=True,
                    max_telegram_per_cycle=5,
                    broadcaster=fake_broadcaster,
                )

            self.assertEqual(recheck_res["telegram_delivery_status"]["sent"], 1)
            self.assertEqual(recheck_res["telegram_delivery_status"]["sent_asins"], ["B09X1H88VP"])
            self.assertEqual(recheck_res["telegram_delivery_status"]["pruned_expired_asins"], ["B07J2Z5DBM"])

            updated_web = json.loads(deals_file.read_text(encoding="utf-8"))
            self.assertEqual([d["asin"] for d in updated_web["deals"]], ["B09X1H88VP"])
            self.assertEqual(updated_web["deals"][0]["price_usd"], 27.99)
            history = json.loads((data_dir / "price_history.json").read_text(encoding="utf-8"))
            self.assertEqual(history["B09X1H88VP"]["last_published_price_usd"], 27.99)


    def test_hd_image_upgrade_and_pillepues_card_renderer(self):
        import io
        from unittest.mock import patch
        from PIL import Image, ImageDraw
        from src.broadcaster.card_image import (
            _load_brand_logo,
            build_image_url_candidates,
            render_offer_card_from_image_bytes,
            upgrade_amazon_image_url,
        )

        brand_logo = _load_brand_logo(98)
        self.assertIsNotNone(brand_logo)
        self.assertEqual(brand_logo.mode, "RGBA")
        self.assertLessEqual(max(brand_logo.size), 98)

        low_res = "https://m.media-amazon.com/images/I/71xuVr0CPbL._AC_UL320_.jpg"
        self.assertEqual(
            upgrade_amazon_image_url(low_res, size=1200),
            "https://m.media-amazon.com/images/I/71xuVr0CPbL._AC_SL1200_.jpg",
        )
        candidates = build_image_url_candidates(low_res)
        self.assertEqual(
            candidates[0],
            "https://m.media-amazon.com/images/I/71xuVr0CPbL._AC_SL1500_.jpg",
        )
        self.assertIn("https://m.media-amazon.com/images/I/71xuVr0CPbL.jpg", candidates)

        # Render portrait image into 1080x1080 uncropped PillePues branded card
        prod = Image.new("RGB", (500, 900), (255, 255, 255))
        draw = ImageDraw.Draw(prod)
        draw.rectangle([(100, 50), (400, 850)], fill=(30, 41, 59))
        buf = io.BytesIO()
        prod.save(buf, format="PNG")

        deal = {
            "asin": "B09715G57M",
            "title": "Keurig K-Express Cafetera K-Cup",
            "price_usd": 59.99,
            "reference_price_usd": 109.99,
            "discount_pct": 45.5,
            "price_cop": 198969,
            "trm_cop": 3316.7,
            "ships_to_colombia": True,
            "free_shipping_co": True,
            "requires_locker": False,
            "tax_free_colombia": True,
            "image_url": low_res,
        }
        rendered = render_offer_card_from_image_bytes(buf.getvalue(), deal)
        with Image.open(io.BytesIO(rendered)) as out_img:
            self.assertEqual(out_img.size, (1080, 1080))

        card = build_telegram_card(deal, associate_tag="pillepues-20")
        self.assertEqual(
            card["photo_url"],
            "https://m.media-amazon.com/images/I/71xuVr0CPbL._AC_SL1200_.jpg",
        )
        self.assertIn("PillePues", card["caption_html"])

        broadcaster = ChannelBroadcaster(telegram_bot_token="fake-token", telegram_chat_id="@pillepues")
        with (
            patch("src.broadcaster.card_image.render_telegram_offer_card_bytes", return_value=rendered),
            patch.object(
                ChannelBroadcaster,
                "_post_photo_bytes_multipart",
                return_value=(200, {"ok": True, "result": {"message_id": 777}}),
            ) as mock_upload,
        ):
            res = broadcaster.send_telegram(card, deal=deal)
            self.assertEqual(res["status"], "sent")
            self.assertEqual(res["upload_mode"], "rendered_pillepues_card")
            mock_upload.assert_called_once()


if __name__ == "__main__":
    unittest.main()
