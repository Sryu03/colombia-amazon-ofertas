from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class Database:
    """SQLite deterministic storage for Zero-Token Amazon Colombia price monitoring."""

    def __init__(self, db_path: str = "/home/antigravity/amazon-colombia-affiliates/data/deals.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        """Create parent directory and SQLite tables: products, price_history, published_deals."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS products (
                    asin TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    category TEXT DEFAULT 'Tecnología',
                    brand TEXT DEFAULT '',
                    price_usd REAL NOT NULL,
                    list_price_usd REAL DEFAULT 0.0,
                    avg_90d_usd REAL DEFAULT 0.0,
                    ships_to_colombia INTEGER DEFAULT 1,
                    free_shipping_co INTEGER DEFAULT 1,
                    rating REAL DEFAULT 4.5,
                    reviews_count INTEGER DEFAULT 0,
                    image_url TEXT DEFAULT '',
                    highlights TEXT DEFAULT '[]',
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    asin TEXT NOT NULL,
                    price_usd REAL NOT NULL,
                    list_price_usd REAL DEFAULT 0.0,
                    avg_90d_usd REAL DEFAULT 0.0,
                    recorded_at TEXT NOT NULL,
                    FOREIGN KEY (asin) REFERENCES products(asin)
                );

                CREATE INDEX IF NOT EXISTS idx_price_history_asin ON price_history(asin);

                CREATE TABLE IF NOT EXISTS published_deals (
                    asin TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    category TEXT DEFAULT 'Tecnología',
                    brand TEXT DEFAULT '',
                    price_usd REAL NOT NULL,
                    list_price_usd REAL DEFAULT 0.0,
                    avg_90d_usd REAL DEFAULT 0.0,
                    reference_price REAL DEFAULT 0.0,
                    discount_pct REAL DEFAULT 0.0,
                    savings_usd REAL DEFAULT 0.0,
                    is_historic_low INTEGER DEFAULT 0,
                    ships_to_colombia INTEGER DEFAULT 1,
                    free_shipping_co INTEGER DEFAULT 1,
                    tax_free_co INTEGER DEFAULT 1,
                    estimated_import_fees_usd REAL DEFAULT 0.0,
                    total_landed_usd REAL DEFAULT 0.0,
                    price_cop REAL DEFAULT 0.0,
                    total_landed_cop REAL DEFAULT 0.0,
                    trm_cop REAL DEFAULT 4150.0,
                    colombia_badge TEXT DEFAULT '',
                    shipping_badge TEXT DEFAULT '',
                    deal_tier TEXT DEFAULT '',
                    affiliate_url TEXT DEFAULT '',
                    image_url TEXT DEFAULT '',
                    rating REAL DEFAULT 4.5,
                    reviews_count INTEGER DEFAULT 0,
                    highlights TEXT DEFAULT '[]',
                    telegram_copy TEXT DEFAULT '',
                    teams_card_json TEXT DEFAULT '{}',
                    raw_json TEXT DEFAULT '{}',
                    published_at TEXT NOT NULL
                );
                """
            )
            conn.commit()

    def upsert_product(self, product: dict[str, Any]) -> None:
        """Insert or update a monitored product in the products table."""
        now_iso = datetime.now(timezone.utc).isoformat()
        highlights = product.get("highlights", [])
        if isinstance(highlights, (list, dict)):
            highlights_str = json.dumps(highlights, ensure_ascii=False)
        else:
            highlights_str = str(highlights or "[]")

        price_usd = float(product.get("price_usd", product.get("current_price", 0.0)))
        list_price_usd = float(product.get("list_price_usd", product.get("list_price", price_usd)))
        avg_90d_usd = float(product.get("avg_90d_usd", product.get("avg_90d", list_price_usd)))

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO products (
                    asin, title, category, brand, price_usd, list_price_usd, avg_90d_usd,
                    ships_to_colombia, free_shipping_co, rating, reviews_count,
                    image_url, highlights, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(asin) DO UPDATE SET
                    title = excluded.title,
                    category = excluded.category,
                    brand = excluded.brand,
                    price_usd = excluded.price_usd,
                    list_price_usd = excluded.list_price_usd,
                    avg_90d_usd = excluded.avg_90d_usd,
                    ships_to_colombia = excluded.ships_to_colombia,
                    free_shipping_co = excluded.free_shipping_co,
                    rating = excluded.rating,
                    reviews_count = excluded.reviews_count,
                    image_url = excluded.image_url,
                    highlights = excluded.highlights,
                    updated_at = excluded.updated_at
                """,
                (
                    str(product["asin"]),
                    str(product.get("title", "")),
                    str(product.get("category", "Tecnología")),
                    str(product.get("brand", "")),
                    price_usd,
                    list_price_usd,
                    avg_90d_usd,
                    int(bool(product.get("ships_to_colombia", True))),
                    int(bool(product.get("free_shipping_co", True))),
                    float(product.get("rating", 4.5)),
                    int(product.get("reviews_count", 0)),
                    str(product.get("image_url", "")),
                    highlights_str,
                    now_iso,
                ),
            )
            conn.commit()

    def record_price(
        self,
        asin: str,
        price_usd: float,
        list_price_usd: float = 0.0,
        avg_90d_usd: float = 0.0,
    ) -> None:
        """Append a price observation into price_history."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO price_history (asin, price_usd, list_price_usd, avg_90d_usd, recorded_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (str(asin), float(price_usd), float(list_price_usd), float(avg_90d_usd), now_iso),
            )
            conn.commit()

    def save_published_deal(self, deal: dict[str, Any]) -> None:
        """Save or update an approved deal in published_deals."""
        now_iso = str(deal.get("published_at") or datetime.now(timezone.utc).isoformat())
        price_usd = float(deal.get("price_usd", deal.get("current_price", 0.0)))
        list_price_usd = float(deal.get("list_price_usd", deal.get("list_price", price_usd)))
        avg_90d_usd = float(deal.get("avg_90d_usd", deal.get("avg_90d", list_price_usd)))
        reference_price = float(deal.get("reference_price", max(list_price_usd, avg_90d_usd)))
        discount_pct = float(deal.get("discount_pct", 0.0))
        savings_usd = float(deal.get("savings_usd", round(max(0.0, reference_price - price_usd), 2)))
        is_historic_low = int(bool(deal.get("is_historic_low", discount_pct >= 35.0)))
        ships_to_colombia = int(bool(deal.get("ships_to_colombia", True)))
        free_shipping_co = int(bool(deal.get("free_shipping_co", price_usd >= 35.0 or deal.get("free_shipping_eligible", True))))
        tax_free_co = int(bool(deal.get("tax_free_co", deal.get("is_tax_free_co", price_usd <= 200.0))))

        highlights = deal.get("highlights", [])
        highlights_str = json.dumps(highlights, ensure_ascii=False) if isinstance(highlights, list) else str(highlights or "[]")

        teams_card = deal.get("teams_card", deal.get("teams_card_json", {}))
        teams_card_str = json.dumps(teams_card, ensure_ascii=False) if isinstance(teams_card, dict) else str(teams_card or "{}")

        raw_copy = dict(deal)
        raw_copy["published_at"] = now_iso
        raw_json_str = json.dumps(raw_copy, ensure_ascii=False)

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO published_deals (
                    asin, title, category, brand, price_usd, list_price_usd, avg_90d_usd,
                    reference_price, discount_pct, savings_usd, is_historic_low,
                    ships_to_colombia, free_shipping_co, tax_free_co,
                    estimated_import_fees_usd, total_landed_usd, price_cop, total_landed_cop, trm_cop,
                    colombia_badge, shipping_badge, deal_tier, affiliate_url, image_url,
                    rating, reviews_count, highlights, telegram_copy, teams_card_json,
                    raw_json, published_at
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?
                )
                ON CONFLICT(asin) DO UPDATE SET
                    title = excluded.title,
                    category = excluded.category,
                    brand = excluded.brand,
                    price_usd = excluded.price_usd,
                    list_price_usd = excluded.list_price_usd,
                    avg_90d_usd = excluded.avg_90d_usd,
                    reference_price = excluded.reference_price,
                    discount_pct = excluded.discount_pct,
                    savings_usd = excluded.savings_usd,
                    is_historic_low = excluded.is_historic_low,
                    ships_to_colombia = excluded.ships_to_colombia,
                    free_shipping_co = excluded.free_shipping_co,
                    tax_free_co = excluded.tax_free_co,
                    estimated_import_fees_usd = excluded.estimated_import_fees_usd,
                    total_landed_usd = excluded.total_landed_usd,
                    price_cop = excluded.price_cop,
                    total_landed_cop = excluded.total_landed_cop,
                    trm_cop = excluded.trm_cop,
                    colombia_badge = excluded.colombia_badge,
                    shipping_badge = excluded.shipping_badge,
                    deal_tier = excluded.deal_tier,
                    affiliate_url = excluded.affiliate_url,
                    image_url = excluded.image_url,
                    rating = excluded.rating,
                    reviews_count = excluded.reviews_count,
                    highlights = excluded.highlights,
                    telegram_copy = excluded.telegram_copy,
                    teams_card_json = excluded.teams_card_json,
                    raw_json = excluded.raw_json,
                    published_at = excluded.published_at
                """,
                (
                    str(deal["asin"]),
                    str(deal.get("title", "")),
                    str(deal.get("category", "Tecnología")),
                    str(deal.get("brand", "")),
                    price_usd,
                    list_price_usd,
                    avg_90d_usd,
                    reference_price,
                    discount_pct,
                    savings_usd,
                    is_historic_low,
                    ships_to_colombia,
                    free_shipping_co,
                    tax_free_co,
                    float(deal.get("estimated_import_fees_usd", 0.0)),
                    float(deal.get("total_landed_usd", price_usd)),
                    float(deal.get("price_cop", 0.0)),
                    float(deal.get("total_landed_cop", deal.get("price_cop", 0.0))),
                    float(deal.get("trm_cop", 4150.0)),
                    str(deal.get("colombia_badge", "")),
                    str(deal.get("shipping_badge", "")),
                    str(deal.get("deal_tier", "")),
                    str(deal.get("affiliate_url", "")),
                    str(deal.get("image_url", "")),
                    float(deal.get("rating", 4.5)),
                    int(deal.get("reviews_count", 0)),
                    highlights_str,
                    str(deal.get("telegram_copy", "")),
                    teams_card_str,
                    raw_json_str,
                    now_iso,
                ),
            )
            conn.commit()

    def get_published_deals(
        self,
        category: str | None = None,
        tax_free_only: bool = False,
        free_shipping_only: bool = False,
        min_discount: float = 0.0,
        search: str | None = None,
    ) -> list[dict[str, Any]]:
        """Query published deals with optional Colombia filters."""
        query = "SELECT * FROM published_deals WHERE 1=1"
        params: list[Any] = []

        if category and category.lower() not in ("all", "todas", "todos"):
            query += " AND LOWER(category) = LOWER(?)"
            params.append(category.strip())

        if tax_free_only:
            query += " AND tax_free_co = 1 AND price_usd <= 200.0"

        if free_shipping_only:
            query += " AND free_shipping_co = 1"

        if min_discount > 0:
            query += " AND discount_pct >= ?"
            params.append(float(min_discount))

        if search and search.strip():
            like_term = f"%{search.strip()}%"
            query += " AND (title LIKE ? OR brand LIKE ? OR category LIKE ? OR asin LIKE ?)"
            params.extend([like_term, like_term, like_term, like_term])

        query += " ORDER BY discount_pct DESC, price_usd ASC"

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()

        results: list[dict[str, Any]] = []
        for row in rows:
            row_dict = dict(row)
            raw_data: dict[str, Any] = {}
            if row_dict.get("raw_json"):
                try:
                    raw_data = json.loads(row_dict["raw_json"])
                except (ValueError, TypeError):
                    raw_data = {}

            try:
                highlights = json.loads(row_dict.get("highlights") or "[]")
            except (ValueError, TypeError):
                highlights = []

            try:
                teams_card = json.loads(row_dict.get("teams_card_json") or "{}")
            except (ValueError, TypeError):
                teams_card = {}

            merged: dict[str, Any] = {
                **raw_data,
                "asin": row_dict["asin"],
                "title": row_dict["title"],
                "category": row_dict["category"],
                "brand": row_dict["brand"],
                "price_usd": float(row_dict["price_usd"]),
                "list_price_usd": float(row_dict["list_price_usd"]),
                "avg_90d_usd": float(row_dict["avg_90d_usd"]),
                "reference_price": float(row_dict["reference_price"]),
                "discount_pct": float(row_dict["discount_pct"]),
                "savings_usd": float(row_dict["savings_usd"]),
                "is_historic_low": bool(row_dict["is_historic_low"]),
                "ships_to_colombia": bool(row_dict["ships_to_colombia"]),
                "free_shipping_co": bool(row_dict["free_shipping_co"]),
                "tax_free_co": bool(row_dict["tax_free_co"]),
                "estimated_import_fees_usd": float(row_dict["estimated_import_fees_usd"]),
                "total_landed_usd": float(row_dict["total_landed_usd"]),
                "price_cop": float(row_dict["price_cop"]),
                "total_landed_cop": float(row_dict["total_landed_cop"]),
                "trm_cop": float(row_dict["trm_cop"]),
                "colombia_badge": row_dict["colombia_badge"],
                "shipping_badge": row_dict["shipping_badge"],
                "deal_tier": row_dict["deal_tier"],
                "affiliate_url": row_dict["affiliate_url"],
                "image_url": row_dict["image_url"],
                "rating": float(row_dict["rating"]),
                "reviews_count": int(row_dict["reviews_count"]),
                "highlights": highlights,
                "telegram_copy": row_dict["telegram_copy"],
                "teams_card": teams_card,
                "published_at": row_dict["published_at"],
            }
            results.append(merged)

        return results

    def clear_stale_published_deals(self, active_asins: list[str]) -> None:
        """Remove published deals that are no longer active in the current cycle."""
        with self._connect() as conn:
            if not active_asins:
                conn.execute("DELETE FROM published_deals")
            else:
                placeholders = ",".join("?" for _ in active_asins)
                conn.execute(
                    f"DELETE FROM published_deals WHERE asin NOT IN ({placeholders})",
                    tuple(active_asins),
                )
            conn.commit()

    def export_deals_json(
        self,
        output_path: str = "/home/antigravity/amazon-colombia-affiliates/public/data/deals.json",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Export all published deals and catalog stats to a static JSON file for the web catalog."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        deals = self.get_published_deals()
        categories = sorted({d["category"] for d in deals if d.get("category")})
        payload: dict[str, Any] = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_deals": len(deals),
            "tax_free_count": sum(1 for d in deals if d.get("tax_free_co")),
            "free_shipping_count": sum(1 for d in deals if d.get("free_shipping_co")),
            "categories": categories,
            "metadata": metadata or {},
            "deals": deals,
        }
        out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return str(out)
