#!/usr/bin/env python3
import argparse
import json
import sqlite3
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from urllib.request import Request, urlopen


BASE_URL = "https://openapi.tcgtracking.com/v1/3"


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def utc_timestamp(value):
    if value is None:
        return None
    return datetime.fromisoformat(value).astimezone(timezone.utc).isoformat(timespec="seconds")


def required_text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"missing or blank {field}")
    return value.strip()


def fetch_json(path):
    request = Request(f"{BASE_URL}{path}", headers={"User-Agent": "PokeCardScan/1"})
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read(), parse_float=Decimal)


def find_set(set_id):
    for source_set in fetch_json("/sets").get("sets", []):
        if source_set.get("id") == set_id:
            return source_set
    raise ValueError(f"English Pokemon set {set_id} was not found")


def initialize_database(connection, schema_path):
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(schema_path.read_text())


def prepare_set(connection, source_set):
    set_id = source_set.get("id")
    if not isinstance(set_id, int) or set_id <= 0:
        raise ValueError("set id must be a positive integer")
    name = required_text(source_set.get("name"), "set name")
    abbreviation = required_text(source_set.get("abbreviation"), "set abbreviation")
    with connection:
        connection.execute(
            """INSERT INTO sets (set_id, name, abbreviation)
               VALUES (?, ?, ?)
               ON CONFLICT(set_id) DO UPDATE SET
                   name = excluded.name,
                   abbreviation = excluded.abbreviation""",
            (set_id, name, abbreviation),
        )


def start_run(connection, set_id, sync_type):
    with connection:
        cursor = connection.execute(
            "INSERT INTO sync_runs (set_id, sync_type, started_at, status) VALUES (?, ?, ?, 'running')",
            (set_id, sync_type, now()),
        )
    return cursor.lastrowid


def finish_run(connection, run_id, status, error_message=None):
    with connection:
        connection.execute(
            "UPDATE sync_runs SET completed_at = ?, status = ?, error_message = ? WHERE sync_run_id = ?",
            (now(), status, error_message, run_id),
        )


def sync_products(connection, source_set, payload):
    set_id = source_set["id"]
    products = payload.get("products")
    if not isinstance(products, list):
        raise ValueError("cards response has no products list")

    run_id = start_run(connection, set_id, "products")
    imported = 0
    try:
        with connection:
            for product in products:
                if product.get("rarity") == "Code Card":
                    continue

                product_id = product.get("id")
                if not isinstance(product_id, int) or product_id <= 0:
                    raise ValueError("product id must be a positive integer")
                name = required_text(product.get("name"), f"name for product {product_id}")
                number = required_text(product.get("number"), f"collector number for product {product_id}")
                rarity = required_text(product.get("rarity"), f"rarity for product {product_id}")

                connection.execute(
                    """INSERT INTO cards (product_id, set_id, name, collector_number, rarity)
                       VALUES (?, ?, ?, ?, ?)
                       ON CONFLICT(product_id) DO UPDATE SET
                           set_id = excluded.set_id,
                           name = excluded.name,
                           collector_number = excluded.collector_number,
                           rarity = excluded.rarity""",
                    (product_id, set_id, name, number, rarity),
                )

                image_url = product.get("image_url")
                if image_url is not None:
                    image_url = required_text(image_url, f"image URL for product {product_id}")
                old_urls = {
                    row[0]
                    for row in connection.execute(
                        "SELECT image_url FROM card_images WHERE product_id = ?", (product_id,)
                    )
                }
                new_urls = {image_url} if image_url else set()
                if old_urls != new_urls:
                    connection.execute("DELETE FROM card_images WHERE product_id = ?", (product_id,))
                    if image_url:
                        connection.execute(
                            "INSERT INTO card_images (product_id, image_url) VALUES (?, ?)",
                            (product_id, image_url),
                        )
                imported += 1

            connection.execute(
                "UPDATE sets SET products_modified_at = ? WHERE set_id = ?",
                (utc_timestamp(source_set.get("products_modified")), set_id),
            )
    except Exception as error:
        finish_run(connection, run_id, "failed", str(error))
        raise
    finish_run(connection, run_id, "succeeded")
    return imported


def price_cents(value):
    amount = Decimal(str(value)) * 100
    if amount < 0 or amount != amount.to_integral_value():
        raise ValueError(f"market price {value!r} is not a nonnegative cent amount")
    return int(amount)


def sync_prices(connection, source_set, payload):
    set_id = source_set["id"]
    prices = payload.get("prices")
    if not isinstance(prices, dict):
        raise ValueError("pricing response has no prices object")

    run_id = start_run(connection, set_id, "pricing")
    imported = 0
    try:
        with connection:
            product_ids = {
                row[0]
                for row in connection.execute("SELECT product_id FROM cards WHERE set_id = ?", (set_id,))
            }
            connection.execute(
                "DELETE FROM prices WHERE product_id IN (SELECT product_id FROM cards WHERE set_id = ?)",
                (set_id,),
            )
            for raw_product_id, product_prices in prices.items():
                product_id = int(raw_product_id)
                if product_id not in product_ids:
                    continue
                tcg_prices = product_prices.get("tcg") or {}
                if not isinstance(tcg_prices, dict):
                    raise ValueError(f"invalid TCG prices for product {product_id}")
                for raw_finish, values in tcg_prices.items():
                    finish = required_text(raw_finish, f"finish for product {product_id}")
                    market = values.get("market")
                    if market is None:
                        continue
                    connection.execute(
                        "INSERT INTO prices (product_id, finish, market_price_cents) VALUES (?, ?, ?)",
                        (product_id, finish, price_cents(market)),
                    )
                    imported += 1

            connection.execute(
                "UPDATE sets SET pricing_modified_at = ? WHERE set_id = ?",
                (utc_timestamp(source_set.get("pricing_modified")), set_id),
            )
    except Exception as error:
        finish_run(connection, run_id, "failed", str(error))
        raise
    finish_run(connection, run_id, "succeeded")
    return imported


def main():
    parser = argparse.ArgumentParser(description="Import one English Pokemon set from TCGTracking")
    parser.add_argument("set_id", type=int)
    parser.add_argument("--database", type=Path, default=Path("catalog.sqlite3"))
    parser.add_argument("--schema", type=Path, default=Path(__file__).with_name("schema.sql"))
    args = parser.parse_args()

    try:
        source_set = find_set(args.set_id)
        cards = fetch_json(f"/sets/{args.set_id}/cards")
        pricing = fetch_json(f"/sets/{args.set_id}/pricing")
        with sqlite3.connect(args.database) as connection:
            initialize_database(connection, args.schema)
            prepare_set(connection, source_set)
            card_count = sync_products(connection, source_set, cards)
            price_count = sync_prices(connection, source_set, pricing)
        print(f"Imported {card_count} cards and {price_count} prices for set {args.set_id}")
    except Exception as error:
        raise SystemExit(f"Import failed: {error}") from error


if __name__ == "__main__":
    main()
