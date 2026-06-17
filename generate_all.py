"""
generate_all.py — runs the full data generation pipeline in dependency order:
products/stores (independent) -> sales+inventory (depends on both).
"""
import subprocess
import sys
import os

SCRIPT_DIR = os.path.dirname(__file__)

STEPS = [
    "generate_products.py",
    "generate_stores.py",
    "generate_sales_inventory.py",
]

if __name__ == "__main__":
    for step in STEPS:
        print(f"\n=== Running {step} ===")
        result = subprocess.run([sys.executable, os.path.join(SCRIPT_DIR, step)])
        if result.returncode != 0:
            print(f"[FAIL] {step} exited with code {result.returncode}")
            sys.exit(1)
    print("\n=== Data generation pipeline complete ===")
