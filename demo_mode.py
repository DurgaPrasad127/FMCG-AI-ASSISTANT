"""
backend/demo_mode.py
--------------------
Rule-based NL→SQL intent matcher used when no Anthropic API key is configured.
Covers 12 common business question patterns using regex matching.

Each intent returns (sql: str, explanation_template: str).
The explanation_template may contain {rows} which is replaced with the
first result row's values for a concise plain-English summary.

Design note: DEMO_MODE is intentionally narrow but correct. It is not a
replacement for the LLM path — it exists purely to keep the prototype fully
runnable/demoable with zero external dependencies.
"""
import re

# ---------------------------------------------------------------------------
# Intent registry
# ---------------------------------------------------------------------------
# Each entry: (priority, compiled_regex, sql, explanation_prefix)
# Matched in priority order (lower number = higher priority).

_INTENTS = [
    # 1. Top products by revenue
    (10, re.compile(r'\b(top|best)\b.{0,30}\bproduct.{0,20}\brevenue\b', re.I),
     """
     SELECT p.product_name, p.category, ROUND(SUM(s.revenue),2) AS total_revenue
     FROM sales s
     JOIN products p ON s.product_id = p.product_id
     GROUP BY s.product_id
     ORDER BY total_revenue DESC
     LIMIT 10
     """,
     "Top 10 products ranked by total revenue"),

    # 2. Top products by units sold
    (11, re.compile(r'\b(top|best)\b.{0,30}\bproduct.{0,20}\bunits\b', re.I),
     """
     SELECT p.product_name, p.category, SUM(s.units_sold) AS total_units
     FROM sales s
     JOIN products p ON s.product_id = p.product_id
     GROUP BY s.product_id
     ORDER BY total_units DESC
     LIMIT 10
     """,
     "Top 10 products ranked by units sold"),

    # 3. Revenue by region
    (20, re.compile(r'\b(region|regional)\b.{0,40}\brevenue\b|\brevenue\b.{0,40}\bregion\b', re.I),
     """
     SELECT region, ROUND(SUM(revenue),2) AS total_revenue,
            SUM(units_sold) AS total_units
     FROM sales
     GROUP BY region
     ORDER BY total_revenue DESC
     """,
     "Revenue breakdown by region"),

    # 4. Revenue by category
    (21, re.compile(r'\b(categor)\w*.{0,40}\brevenue\b|\brevenue\b.{0,40}\bcategor\b', re.I),
     """
     SELECT p.category, ROUND(SUM(s.revenue),2) AS total_revenue,
            SUM(s.units_sold) AS total_units
     FROM sales s
     JOIN products p ON s.product_id = p.product_id
     GROUP BY p.category
     ORDER BY total_revenue DESC
     """,
     "Revenue breakdown by product category"),

    # 5. Revenue by store format
    (22, re.compile(r'\b(store.?format|format)\b.{0,40}\brevenue\b|\brevenue\b.{0,40}\bformat\b', re.I),
     """
     SELECT st.store_format, ROUND(SUM(s.revenue),2) AS total_revenue,
            SUM(s.units_sold) AS total_units, COUNT(DISTINCT st.store_id) AS num_stores
     FROM sales s
     JOIN stores st ON s.store_id = st.store_id
     GROUP BY st.store_format
     ORDER BY total_revenue DESC
     """,
     "Revenue and units by store format"),

    # 6. Promotion impact / lift
    (30, re.compile(r'\bpromo(tion)?\b.{0,50}\b(impact|lift|effect|uplift|performance)\b'
                    r'|\b(impact|lift|effect|uplift)\b.{0,30}\bpromo\b', re.I),
     """
     SELECT promotion_flag,
            COUNT(*) AS weeks,
            ROUND(AVG(units_sold),2) AS avg_units,
            ROUND(AVG(revenue),2) AS avg_revenue
     FROM sales
     GROUP BY promotion_flag
     ORDER BY promotion_flag DESC
     """,
     "Average sales performance: promotion weeks vs. non-promotion weeks"),

    # 7. Promotion type breakdown
    (31, re.compile(r'\bpromo(tion)?.{0,30}\btype\b|\btype.{0,30}\bpromo\b', re.I),
     """
     SELECT promotion_type, COUNT(*) AS promo_weeks,
            ROUND(AVG(units_sold),2) AS avg_units,
            ROUND(AVG(discount_pct*100),1) AS avg_discount_pct
     FROM sales
     WHERE promotion_flag = 1
     GROUP BY promotion_type
     ORDER BY avg_units DESC
     """,
     "Performance breakdown by promotion type"),

    # 8. Stockout analysis
    (40, re.compile(r'\bstockout\b', re.I),
     """
     SELECT p.product_name, p.category, st.region,
            SUM(i.stockout_flag) AS stockout_weeks,
            COUNT(*) AS total_weeks,
            ROUND(100.0*SUM(i.stockout_flag)/COUNT(*),1) AS stockout_rate_pct
     FROM inventory i
     JOIN products p ON i.product_id = p.product_id
     JOIN stores st ON i.store_id = st.store_id
     GROUP BY i.product_id, st.region
     HAVING stockout_weeks > 0
     ORDER BY stockout_weeks DESC
     LIMIT 15
     """,
     "Products and regions with the most stockout weeks"),

    # 9. Weekly revenue trend
    (50, re.compile(r'\b(week(ly)?|trend)\b.{0,40}\brevenue\b|\brevenue\b.{0,40}\b(trend|week)\b', re.I),
     """
     SELECT week_start_date,
            ROUND(SUM(revenue),2) AS weekly_revenue,
            SUM(units_sold) AS weekly_units
     FROM sales
     GROUP BY week_start_date
     ORDER BY week_start_date
     """,
     "Weekly revenue and units trend over the 24-week period"),

    # 10. Brand performance
    (60, re.compile(r'\bbrand\b', re.I),
     """
     SELECT p.brand, ROUND(SUM(s.revenue),2) AS total_revenue,
            SUM(s.units_sold) AS total_units,
            COUNT(DISTINCT p.product_id) AS skus
     FROM sales s
     JOIN products p ON s.product_id = p.product_id
     GROUP BY p.brand
     ORDER BY total_revenue DESC
     """,
     "Revenue and units broken down by brand"),

    # 11. Low/worst performing products
    (70, re.compile(r'\b(worst|lowest|low.?performing|underperform)\b', re.I),
     """
     SELECT p.product_name, p.category, ROUND(SUM(s.revenue),2) AS total_revenue,
            SUM(s.units_sold) AS total_units
     FROM sales s
     JOIN products p ON s.product_id = p.product_id
     GROUP BY s.product_id
     ORDER BY total_revenue ASC
     LIMIT 10
     """,
     "Bottom 10 products by total revenue"),

    # 12. Inventory / stock levels
    (80, re.compile(r'\b(inventory|stock|replenish)\b', re.I),
     """
     SELECT p.product_name, p.category,
            ROUND(AVG(i.closing_stock),1) AS avg_closing_stock,
            SUM(i.units_received) AS total_replenishments,
            SUM(i.stockout_flag) AS stockout_weeks
     FROM inventory i
     JOIN products p ON i.product_id = p.product_id
     GROUP BY i.product_id
     ORDER BY avg_closing_stock ASC
     LIMIT 15
     """,
     "Inventory levels and replenishment summary by product"),
]

# Sort by priority once at import time
_INTENTS.sort(key=lambda x: x[0])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def match(question: str) -> tuple[str, str] | None:
    """
    Try to match *question* against the intent registry.

    Returns (sql, description) if matched, or None if no intent matches.
    """
    for _, pattern, sql, description in _INTENTS:
        if pattern.search(question):
            return sql.strip(), description
    return None


def fallback_sql() -> tuple[str, str]:
    """Return a safe default query when no intent matches."""
    sql = """
    SELECT p.category,
           ROUND(SUM(s.revenue),2) AS total_revenue,
           SUM(s.units_sold) AS total_units
    FROM sales s
    JOIN products p ON s.product_id = p.product_id
    GROUP BY p.category
    ORDER BY total_revenue DESC
    """.strip()
    description = (
        "No specific intent matched — showing overall revenue by category. "
        "Try asking about: top products, revenue by region, promotion impact, "
        "stockouts, weekly trends, brand performance, or inventory levels."
    )
    return sql, description
