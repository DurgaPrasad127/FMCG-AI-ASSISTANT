"""
generate_products.py
---------------------
Generates the Product Master dataset for the FMCG Beverages AI Assistant.

Design notes (documented for the M5 "Dataset Rationale" submission):
- 18 SKUs across 5 categories (Carbonated, Juice, Water, Energy, Dairy) so the
  assistant has enough category diversity to answer "compare categories" /
  "which sub-category sells best" style questions without the dataset being
  unwieldy to reason about by hand during evaluation.
- All brand and product names are fictional to avoid using real, trademarked
  FMCG brands in a synthetic dataset.
- unit_price is set with realistic price banding by category and pack size
  (e.g. energy drinks priced per-ml higher than water) so that revenue
  calculations downstream look like real retail economics, not noise.
"""

import csv
import os

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "raw", "products.csv")

# (product_id, product_name, brand, category, sub_category, pack_size_ml, unit_price)
PRODUCTS = [
    ("BEV-001", "Spark Lemon Sparkling Water 500ml", "Spark", "Carbonated", "Sparkling Water", 500, 1.49),
    ("BEV-002", "Spark Classic Cola 500ml", "Spark", "Carbonated", "Cola", 500, 1.69),
    ("BEV-003", "Spark Classic Cola 1500ml", "Spark", "Carbonated", "Cola", 1500, 2.99),
    ("BEV-004", "FizzPop Orange Soda 330ml", "FizzPop", "Carbonated", "Flavoured Soda", 330, 1.29),
    ("BEV-005", "FizzPop Ginger Ale 330ml", "FizzPop", "Carbonated", "Flavoured Soda", 330, 1.29),
    ("BEV-006", "PureSpring Still Water 500ml", "PureSpring", "Water", "Still Water", 500, 0.79),
    ("BEV-007", "PureSpring Still Water 1000ml", "PureSpring", "Water", "Still Water", 1000, 1.19),
    ("BEV-008", "PureSpring Sparkling Mineral Water 750ml", "PureSpring", "Water", "Sparkling Water", 750, 1.59),
    ("BEV-009", "Orchardly Orange Juice 1000ml", "Orchardly", "Juice", "Fruit Juice", 1000, 3.49),
    ("BEV-010", "Orchardly Apple Juice 1000ml", "Orchardly", "Juice", "Fruit Juice", 1000, 3.29),
    ("BEV-011", "Orchardly Mixed Berry Juice 250ml", "Orchardly", "Juice", "Fruit Juice", 250, 1.49),
    ("BEV-012", "TropiBlend Mango Juice 1000ml", "TropiBlend", "Juice", "Fruit Juice", 1000, 3.59),
    ("BEV-013", "VoltUp Energy Drink 250ml", "VoltUp", "Energy", "Energy Drink", 250, 2.19),
    ("BEV-014", "VoltUp Sugar-Free Energy Drink 250ml", "VoltUp", "Energy", "Energy Drink", 250, 2.29),
    ("BEV-015", "RushPeak Energy Drink 500ml", "RushPeak", "Energy", "Energy Drink", 500, 3.49),
    ("BEV-016", "DairyDrop Chocolate Milk Drink 350ml", "DairyDrop", "Dairy", "Flavoured Milk", 350, 1.89),
    ("BEV-017", "DairyDrop Strawberry Milk Drink 350ml", "DairyDrop", "Dairy", "Flavoured Milk", 350, 1.89),
    ("BEV-018", "AthleteAde Sports Drink 500ml", "AthleteAde", "Energy", "Sports Drink", 500, 1.99),
]


def validate(rows):
    ids = [r[0] for r in rows]
    assert len(ids) == len(set(ids)), "Duplicate product_id detected"
    for r in rows:
        pid, name, brand, cat, subcat, pack, price = r
        assert pid.startswith("BEV-"), f"Bad product_id format: {pid}"
        assert pack > 0, f"Invalid pack size for {pid}"
        assert price > 0, f"Invalid price for {pid}"
    print(f"[OK] {len(rows)} products validated across "
          f"{len(set(r[3] for r in rows))} categories.")


def main():
    validate(PRODUCTS)
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "product_id", "product_name", "brand", "category",
            "sub_category", "pack_size_ml", "unit_price",
        ])
        writer.writerows(PRODUCTS)
    print(f"[OK] Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
