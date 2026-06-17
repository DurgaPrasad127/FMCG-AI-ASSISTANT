"""
generate_stores.py
-------------------
Generates the Store Master dataset.

Design notes:
- 40 stores across 4 regions (North, South, East, West), 10 stores per
  region, so region-level aggregate comparisons are statistically meaningful
  (enough stores per region to average out noise) without the dataset
  becoming too large to inspect manually.
- store_format mix is deliberately uneven (more Supermarket/Convenience,
  fewer Hypermarket/Wholesale) to mirror a realistic retail footprint -
  this also gives the assistant something non-trivial to reason about when
  asked "which store format performs best".
- A baseline_demand_index is NOT stored in this table (it's not part of the
  brief's schema) but is used internally by generate_sales_inventory.py to
  drive realistic volume differences between stores; see that script.
"""

import csv
import os
import random

random.seed(42)

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "raw", "stores.csv")

REGIONS = {
    "North": ["Brighton Falls", "Millhaven", "Eastwick", "Northgate"],
    "South": ["Suncrest", "Palmridge", "Bayport", "Southfield"],
    "East": ["Rivermouth", "Harborview", "Eastbrook", "Cliffside"],
    "West": ["Westfield", "Goldvale", "Pinecrest", "Sierraton"],
}

# Weighted store format mix
FORMAT_WEIGHTS = [
    ("Supermarket", 0.40),
    ("Convenience", 0.30),
    ("Hypermarket", 0.15),
    ("Wholesale", 0.15),
]

STORE_NAME_PREFIXES = ["FreshMart", "QuickStop", "MegaBasket", "CornerShop",
                        "ValueGrocer", "DailyNeeds", "MarketPlace", "primeBuy"]


def weighted_format():
    formats, weights = zip(*FORMAT_WEIGHTS)
    return random.choices(formats, weights=weights, k=1)[0]


def generate_stores(n_stores=40):
    rows = []
    regions_cycle = list(REGIONS.keys())
    stores_per_region = n_stores // len(regions_cycle)
    store_num = 1
    for region in regions_cycle:
        cities = REGIONS[region]
        for i in range(stores_per_region):
            city = cities[i % len(cities)]
            fmt = weighted_format()
            prefix = random.choice(STORE_NAME_PREFIXES)
            suffix = random.choice(["Central", "Plaza", "Southside", "Junction",
                                     "Square", "Crossing", "Heights", "Market"])
            store_id = f"STR-{store_num:03d}"
            store_name = f"{prefix} {suffix}"
            rows.append((store_id, store_name, region, city, fmt))
            store_num += 1
    return rows


def validate(rows):
    ids = [r[0] for r in rows]
    assert len(ids) == len(set(ids)), "Duplicate store_id detected"
    regions = set(r[2] for r in rows)
    assert len(regions) == 4, f"Expected 4 regions, got {len(regions)}"
    for r in rows:
        assert r[0].startswith("STR-"), f"Bad store_id format: {r[0]}"
    print(f"[OK] {len(rows)} stores validated across {len(regions)} regions: "
          f"{sorted(regions)}")


def main():
    rows = generate_stores(40)
    validate(rows)
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["store_id", "store_name", "region", "city", "store_format"])
        writer.writerows(rows)
    print(f"[OK] Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
