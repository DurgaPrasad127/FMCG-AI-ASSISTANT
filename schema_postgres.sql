-- schema_postgres.sql
-- PostgreSQL schema for the FMCG Beverages AI Insights Assistant.
-- Uses native BOOLEAN, NUMERIC, GENERATED identity columns, and ENUM-style
-- CHECK constraints for portability (avoiding actual CREATE TYPE enums so
-- the schema stays simple to migrate/alter later).

DROP TABLE IF EXISTS inventory;
DROP TABLE IF EXISTS sales;
DROP TABLE IF EXISTS stores;
DROP TABLE IF EXISTS products;

CREATE TABLE products (
    product_id      VARCHAR(20) PRIMARY KEY,
    product_name    VARCHAR(255) NOT NULL,
    brand            VARCHAR(100) NOT NULL,
    category        VARCHAR(50) NOT NULL,
    sub_category    VARCHAR(100) NOT NULL,
    pack_size_ml    INTEGER NOT NULL CHECK (pack_size_ml > 0),
    unit_price      NUMERIC(10,2) NOT NULL CHECK (unit_price > 0)
);

CREATE TABLE stores (
    store_id        VARCHAR(20) PRIMARY KEY,
    store_name      VARCHAR(255) NOT NULL,
    region          VARCHAR(20) NOT NULL CHECK (region IN ('North','South','East','West')),
    city            VARCHAR(100) NOT NULL,
    store_format    VARCHAR(50) NOT NULL CHECK (store_format IN
                        ('Supermarket','Hypermarket','Convenience','Wholesale'))
);

CREATE TABLE sales (
    sale_id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    week_start_date DATE NOT NULL,
    product_id      VARCHAR(20) NOT NULL REFERENCES products(product_id),
    store_id        VARCHAR(20) NOT NULL REFERENCES stores(store_id),
    region          VARCHAR(20) NOT NULL,
    units_sold      INTEGER NOT NULL CHECK (units_sold >= 0),
    revenue         NUMERIC(12,2) NOT NULL CHECK (revenue >= 0),
    promotion_flag  BOOLEAN NOT NULL DEFAULT FALSE,
    promotion_type  VARCHAR(50),
    discount_pct    NUMERIC(4,3) NOT NULL DEFAULT 0 CHECK (discount_pct >= 0 AND discount_pct <= 1),
    CONSTRAINT uq_sales_key UNIQUE (week_start_date, product_id, store_id)
);

CREATE TABLE inventory (
    inventory_id    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    week_start_date DATE NOT NULL,
    product_id      VARCHAR(20) NOT NULL REFERENCES products(product_id),
    store_id        VARCHAR(20) NOT NULL REFERENCES stores(store_id),
    opening_stock   INTEGER NOT NULL CHECK (opening_stock >= 0),
    units_received  INTEGER NOT NULL CHECK (units_received >= 0),
    units_sold      INTEGER NOT NULL CHECK (units_sold >= 0),
    closing_stock   INTEGER NOT NULL CHECK (closing_stock >= 0),
    stockout_flag   BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT uq_inventory_key UNIQUE (week_start_date, product_id, store_id)
);

CREATE INDEX idx_sales_week ON sales(week_start_date);
CREATE INDEX idx_sales_product ON sales(product_id);
CREATE INDEX idx_sales_store ON sales(store_id);
CREATE INDEX idx_sales_region ON sales(region);
CREATE INDEX idx_sales_promo ON sales(promotion_flag) WHERE promotion_flag = TRUE;

CREATE INDEX idx_inventory_week ON inventory(week_start_date);
CREATE INDEX idx_inventory_product ON inventory(product_id);
CREATE INDEX idx_inventory_store ON inventory(store_id);
CREATE INDEX idx_inventory_stockout ON inventory(stockout_flag) WHERE stockout_flag = TRUE;
