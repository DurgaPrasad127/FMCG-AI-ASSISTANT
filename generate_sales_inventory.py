"""
generate_sales_inventory.py
----------------------------
Generates the Sales & Promotions dataset and the Inventory dataset together,
in a single simulation, because the two are causally linked: a stockout in
the Inventory table should suppress units_sold in the Sales table for that
same week, and promotions should draw stock down faster. Generating them
independently (as two unrelated random scripts) was the most obvious first
approach but produces internally inconsistent data (e.g. "sold" units that
exceed available stock) - documented in M5 "Challenges" / M6 "issue faced"
as the reason this is one simulation, not two.

Simulation model (weekly, per product x store):
1. Baseline weekly demand = category_popularity x store_format_multiplier x
   region_multiplier x seasonal_factor(week) x random noise.
2. Promotion calendar: each product gets 2-4 promo windows (1-3 weeks each)
   over the 24-week horizon, run at a random subset of stores. Promotion
   type drives both the discount_pct and the demand uplift multiplier:
       Price Cut         -> uplift 1.3x-1.6x,  discount 10%-25%
       BOGO               -> uplift 1.8x-2.3x,  discount ~50% (effective)
       Display Feature    -> uplift 1.2x-1.4x,  discount 0%-10%
       Bundle              -> uplift 1.4x-1.7x,  discount 15%-30%
3. Inventory is simulated with a simple (s, S) reorder-point policy with a
   1-week replenishment lead time, so promo weeks that exceed what the
   store anticipated can realistically trigger stockouts.
4. units_sold actually recorded = min(demand, opening_stock + units_received)
   -> this is what makes "did stockouts suppress sales" a real, queryable
   pattern in the data rather than a label bolted on afterward.

Run: python generate_sales_inventory.py
Outputs: ../raw/sales.csv, ../raw/inventory.csv
"""

import csv
import math
import os
import random
from datetime import date, timedelta

random.seed(7)

SCRIPT_DIR = os.path.dirname(__file__)
RAW_DIR = os.path.join(SCRIPT_DIR, "..", "raw")
PRODUCTS_CSV = os.path.join(RAW_DIR, "products.csv")
STORES_CSV = os.path.join(RAW_DIR, "stores.csv")
SALES_OUT = os.path.join(RAW_DIR, "sales.csv")
INVENTORY_OUT = os.path.join(RAW_DIR, "inventory.csv")

N_WEEKS = 24
START_DATE = date(2024, 1, 1)

CATEGORY_BASE_DEMAND = {
    "Carbonated": 38,
    "Water": 46,
    "Juice": 22,
    "Energy": 18,
    "Dairy": 16,
}

STORE_FORMAT_MULT = {
    "Hypermarket": 2.4,
    "Supermarket": 1.5,
    "Convenience": 0.6,
    "Wholesale": 1.9,
}

# Relative regional demand strength (e.g. North = larger/denser market)
REGION_MULT = {
    "North": 1.25,
    "South": 1.05,
    "East": 0.90,
    "West": 0.85,
}

PROMO_TYPES = {
    "Price Cut": {"uplift": (1.3, 1.6), "discount": (0.10, 0.25)},
    "BOGO": {"uplift": (1.8, 2.3), "discount": (0.45, 0.50)},
    "Display Feature": {"uplift": (1.2, 1.4), "discount": (0.0, 0.10)},
    "Bundle": {"uplift": (1.4, 1.7), "discount": (0.15, 0.30)},
}


def load_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def seasonal_factor(category, week_idx):
    """Returns a multiplier >0 capturing simple seasonal effects across the
    24-week horizon (roughly Jan-Jun). Energy/Water trend up as weeks
    progress (warmer weather); Dairy/Juice are comparatively flat; a mild
    new-year dip in week 0-1 affects everything slightly."""
    t = week_idx / max(N_WEEKS - 1, 1)
    new_year_dip = 0.92 if week_idx <= 1 else 1.0
    if category in ("Water", "Energy"):
        warm_up = 0.85 + 0.40 * t  # ramps up toward "summer"
    elif category == "Carbonated":
        warm_up = 0.90 + 0.25 * t
    else:  # Juice, Dairy: comparatively stable
        warm_up = 0.95 + 0.10 * math.sin(t * math.pi)
    return round(new_year_dip * warm_up, 3)


def build_promo_calendar(products, stores, weeks):
    """Assigns each product 2-4 promo windows; each window applies to a
    random subset (40%-80%) of stores. Returns:
        promo_lookup[(product_id, store_id, week_idx)] = (promo_type, discount_pct)
    """
    promo_lookup = {}
    store_ids = [s["store_id"] for s in stores]

    for p in products:
        n_windows = random.randint(2, 4)
        used_weeks = set()
        for _ in range(n_windows):
            length = random.randint(1, 3)
            start = random.randint(0, weeks - length)
            window = set(range(start, start + length))
            if window & used_weeks:
                continue  # skip overlapping windows for cleaner signal
            used_weeks |= window

            promo_type = random.choice(list(PROMO_TYPES.keys()))
            cfg = PROMO_TYPES[promo_type]
            discount = round(random.uniform(*cfg["discount"]), 2)

            store_coverage = random.uniform(0.4, 0.8)
            chosen_stores = random.sample(
                store_ids, k=max(1, int(len(store_ids) * store_coverage))
            )
            for st in chosen_stores:
                for w in window:
                    promo_lookup[(p["product_id"], st, w)] = (promo_type, discount)
    return promo_lookup


def simulate():
    products = load_csv(PRODUCTS_CSV)
    stores = load_csv(STORES_CSV)
    promo_lookup = build_promo_calendar(products, stores, N_WEEKS)

    sales_rows = []
    inventory_rows = []

    for p in products:
        category = p["category"]
        base_demand = CATEGORY_BASE_DEMAND[category]
        unit_price = float(p["unit_price"])

        for s in stores:
            fmt_mult = STORE_FORMAT_MULT[s["store_format"]]
            region_mult = REGION_MULT[s["region"]]

            # (s, S) inventory policy parameters, sized off typical weekly demand
            typical_weekly_demand = base_demand * fmt_mult * region_mult
            target_level = int(typical_weekly_demand * 3.0)   # ~3 weeks cover
            reorder_point = int(typical_weekly_demand * 1.2)  # ~1.2 weeks cover

            opening_stock = target_level
            pending_delivery = 0  # arrives next week (1-week lead time)

            for w in range(N_WEEKS):
                week_date = START_DATE + timedelta(weeks=w)

                promo_info = promo_lookup.get((p["product_id"], s["store_id"], w))
                promo_flag = promo_info is not None
                promo_type, discount_pct = (promo_info if promo_info
                                             else (None, 0.0))
                uplift = 1.0
                if promo_flag:
                    lo, hi = PROMO_TYPES[promo_type]["uplift"]
                    uplift = random.uniform(lo, hi)

                noise = random.uniform(0.85, 1.15)
                seas = seasonal_factor(category, w)
                demand = typical_weekly_demand * seas * uplift * noise
                demand = max(0, round(demand))

                units_received = pending_delivery
                available = opening_stock + units_received
                units_sold = min(demand, available)
                closing_stock = available - units_sold
                stockout_flag = closing_stock <= 0 and demand > available

                sales_rows.append({
                    "week_start_date": week_date.isoformat(),
                    "product_id": p["product_id"],
                    "store_id": s["store_id"],
                    "region": s["region"],
                    "units_sold": units_sold,
                    "revenue": round(units_sold * unit_price * (1 - discount_pct), 2),
                    "promotion_flag": promo_flag,
                    "promotion_type": promo_type if promo_flag else "",
                    "discount_pct": discount_pct if promo_flag else 0.0,
                })

                inventory_rows.append({
                    "week_start_date": week_date.isoformat(),
                    "product_id": p["product_id"],
                    "store_id": s["store_id"],
                    "opening_stock": opening_stock,
                    "units_received": units_received,
                    "units_sold": units_sold,
                    "closing_stock": closing_stock,
                    "stockout_flag": stockout_flag,
                })

                # Reorder decision for NEXT week's delivery (1-week lead time)
                if closing_stock < reorder_point:
                    order_qty = max(0, target_level - closing_stock)
                    # Occasional supplier variability: 10% chance of a short delivery
                    if random.random() < 0.10:
                        order_qty = int(order_qty * random.uniform(0.5, 0.85))
                    pending_delivery = order_qty
                else:
                    pending_delivery = 0

                opening_stock = closing_stock

    return sales_rows, inventory_rows


def validate(sales_rows, inventory_rows):
    assert len(sales_rows) == len(inventory_rows), "Row count mismatch between sales/inventory"
    n_promo_weeks = sum(1 for r in sales_rows if r["promotion_flag"])
    n_stockout_weeks = sum(1 for r in inventory_rows if r["stockout_flag"])
    assert n_promo_weeks > 0, "No promotions generated - check promo calendar logic"
    assert n_stockout_weeks > 0, "No stockouts generated - inventory policy too generous"

    # Cross-check: sales.units_sold must equal inventory.units_sold for same key
    key_sales = {(r["product_id"], r["store_id"], r["week_start_date"]): r["units_sold"]
                 for r in sales_rows}
    for r in inventory_rows:
        key = (r["product_id"], r["store_id"], r["week_start_date"])
        assert key_sales[key] == r["units_sold"], f"units_sold mismatch at {key}"

    print(f"[OK] {len(sales_rows)} sales rows, {len(inventory_rows)} inventory rows.")
    print(f"[OK] {n_promo_weeks} promo-active rows "
          f"({n_promo_weeks/len(sales_rows):.1%} of all rows).")
    print(f"[OK] {n_stockout_weeks} stockout rows "
          f"({n_stockout_weeks/len(inventory_rows):.1%} of all rows).")
    print("[OK] sales/inventory units_sold cross-check passed.")


def write_csv(path, rows, fieldnames):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"[OK] Wrote {path}")


def main():
    sales_rows, inventory_rows = simulate()
    validate(sales_rows, inventory_rows)
    write_csv(SALES_OUT, sales_rows, [
        "week_start_date", "product_id", "store_id", "region", "units_sold",
        "revenue", "promotion_flag", "promotion_type", "discount_pct",
    ])
    write_csv(INVENTORY_OUT, inventory_rows, [
        "week_start_date", "product_id", "store_id", "opening_stock",
        "units_received", "units_sold", "closing_stock", "stockout_flag",
    ])


if __name__ == "__main__":
    main()
