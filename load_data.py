"""
load_data.py
------------
Builds the SQLite database (fmcg.db) from the generated CSVs in data/raw/
and the schema in schema_sqlite.sql. Also runs a few sanity queries so a
broken load fails loudly instead of silently producing an empty/partial DB.

Usage:
    python load_data.py
"""
import csv
import os
import sqlite3

DB_DIR = os.path.dirname(__file__)
RAW_DIR = os.path.join(DB_DIR, "..", "raw")
SCHEMA_PATH = os.path.join(DB_DIR, "schema_sqlite.sql")
DB_PATH = os.path.join(DB_DIR, "fmcg.db")


def load_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def to_bool_int(v):
    return 1 if str(v).strip().lower() in ("true", "1") else 0


def main():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    with open(SCHEMA_PATH) as f:
        cur.executescript(f.read())

    products = load_csv(os.path.join(RAW_DIR, "products.csv"))
    cur.executemany(
        """INSERT INTO products (product_id, product_name, brand, category,
           sub_category, pack_size_ml, unit_price) VALUES (?,?,?,?,?,?,?)""",
        [(p["product_id"], p["product_name"], p["brand"], p["category"],
          p["sub_category"], int(p["pack_size_ml"]), float(p["unit_price"]))
         for p in products],
    )

    stores = load_csv(os.path.join(RAW_DIR, "stores.csv"))
    cur.executemany(
        """INSERT INTO stores (store_id, store_name, region, city, store_format)
           VALUES (?,?,?,?,?)""",
        [(s["store_id"], s["store_name"], s["region"], s["city"], s["store_format"])
         for s in stores],
    )

    sales = load_csv(os.path.join(RAW_DIR, "sales.csv"))
    cur.executemany(
        """INSERT INTO sales (week_start_date, product_id, store_id, region,
           units_sold, revenue, promotion_flag, promotion_type, discount_pct)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        [(r["week_start_date"], r["product_id"], r["store_id"], r["region"],
          int(r["units_sold"]), float(r["revenue"]), to_bool_int(r["promotion_flag"]),
          r["promotion_type"] or None, float(r["discount_pct"]))
         for r in sales],
    )

    inventory = load_csv(os.path.join(RAW_DIR, "inventory.csv"))
    cur.executemany(
        """INSERT INTO inventory (week_start_date, product_id, store_id,
           opening_stock, units_received, units_sold, closing_stock, stockout_flag)
           VALUES (?,?,?,?,?,?,?,?)""",
        [(r["week_start_date"], r["product_id"], r["store_id"],
          int(r["opening_stock"]), int(r["units_received"]), int(r["units_sold"]),
          int(r["closing_stock"]), to_bool_int(r["stockout_flag"]))
         for r in inventory],
    )

    conn.commit()

    # Sanity checks
    checks = {
        "products": "SELECT COUNT(*) FROM products",
        "stores": "SELECT COUNT(*) FROM stores",
        "sales": "SELECT COUNT(*) FROM sales",
        "inventory": "SELECT COUNT(*) FROM inventory",
    }
    for name, q in checks.items():
        count = cur.execute(q).fetchone()[0]
        assert count > 0, f"{name} table is empty after load!"
        print(f"[OK] {name}: {count} rows")

    orphan_sales = cur.execute(
        """SELECT COUNT(*) FROM sales s
           LEFT JOIN products p ON s.product_id = p.product_id
           WHERE p.product_id IS NULL"""
    ).fetchone()[0]
    assert orphan_sales == 0, "Found sales rows with no matching product (FK integrity issue)"
    print("[OK] No orphaned foreign keys in sales.")

    conn.close()
    print(f"[OK] Database built at {DB_PATH}")


if __name__ == "__main__":
    main()
