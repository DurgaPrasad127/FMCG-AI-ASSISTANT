-- schema_sqlite.sql
-- SQLite schema for the FMCG Beverages AI Insights Assistant.
-- SQLite has no native BOOLEAN/DECIMAL types; booleans are stored as
-- INTEGER (0/1) and money/decimals as REAL, which is standard SQLite practice.

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS inventory;
DROP TABLE IF EXISTS sales;
DROP TABLE IF EXISTS stores;
DROP TABLE IF EXISTS products;

CREATE TABLE products (
    product_id      TEXT PRIMARY KEY,
    product_name    TEXT NOT NULL,
    brand           TEXT NOT NULL,
    category        TEXT NOT NULL,
    sub_category    TEXT NOT NULL,
    pack_size_ml    INTEGER NOT NULL CHECK (pack_size_ml > 0),
    unit_price      REAL NOT NULL CHECK (unit_price > 0)
);

CREATE TABLE stores (
    store_id        TEXT PRIMARY KEY,
    store_name      TEXT NOT NULL,
    region          TEXT NOT NULL CHECK (region IN ('North','South','East','West')),
    city            TEXT NOT NULL,
    store_format    TEXT NOT NULL CHECK (store_format IN
                        ('Supermarket','Hypermarket','Convenience','Wholesale'))
);

CREATE TABLE sales (
    sale_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    week_start_date TEXT NOT NULL,         -- ISO date string, e.g. 2024-01-01
    product_id      TEXT NOT NULL REFERENCES products(product_id),
    store_id        TEXT NOT NULL REFERENCES stores(store_id),
    region          TEXT NOT NULL,         -- denormalised for query convenience
    units_sold      INTEGER NOT NULL CHECK (units_sold >= 0),
    revenue         REAL NOT NULL CHECK (revenue >= 0),
    promotion_flag  INTEGER NOT NULL CHECK (promotion_flag IN (0,1)),
    promotion_type  TEXT,                  -- NULL when promotion_flag = 0
    discount_pct    REAL NOT NULL DEFAULT 0 CHECK (discount_pct >= 0 AND discount_pct <= 1),
    UNIQUE (week_start_date, product_id, store_id)
);

CREATE TABLE inventory (
    inventory_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    week_start_date TEXT NOT NULL,
    product_id      TEXT NOT NULL REFERENCES products(product_id),
    store_id        TEXT NOT NULL REFERENCES stores(store_id),
    opening_stock   INTEGER NOT NULL CHECK (opening_stock >= 0),
    units_received  INTEGER NOT NULL CHECK (units_received >= 0),
    units_sold      INTEGER NOT NULL CHECK (units_sold >= 0),
    closing_stock   INTEGER NOT NULL CHECK (closing_stock >= 0),
    stockout_flag   INTEGER NOT NULL CHECK (stockout_flag IN (0,1)),
    UNIQUE (week_start_date, product_id, store_id)
);

-- Indexes: the AI layer will mostly filter/group by date range, product,
-- store and region, so these are the access patterns to optimise for.
CREATE INDEX idx_sales_week ON sales(week_start_date);
CREATE INDEX idx_sales_product ON sales(product_id);
CREATE INDEX idx_sales_store ON sales(store_id);
CREATE INDEX idx_sales_region ON sales(region);
CREATE INDEX idx_sales_promo ON sales(promotion_flag);

CREATE INDEX idx_inventory_week ON inventory(week_start_date);
CREATE INDEX idx_inventory_product ON inventory(product_id);
CREATE INDEX idx_inventory_store ON inventory(store_id);
CREATE INDEX idx_inventory_stockout ON inventory(stockout_flag);
