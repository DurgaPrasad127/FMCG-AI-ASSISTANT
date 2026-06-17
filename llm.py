"""
backend/llm.py
--------------
NL→SQL via Anthropic Claude.

Architecture:
  User question  →  system prompt (schema + examples)  →  Claude
  Claude returns a JSON block with {sql, explanation}
  query_guard.validate() checks the SQL before it reaches the DB.

Falls back to demo_mode.match() automatically when DEMO_MODE = True.
"""
import json
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from backend import demo_mode
from backend.db import get_schema_ddl

# ---------------------------------------------------------------------------
# System prompt template
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT_TEMPLATE = """
You are an expert SQL analyst for an FMCG Beverages company. Your role is to
convert natural-language business questions into precise, correct SQLite SQL
queries, then explain the result in plain English.

## Database Schema
{schema}

## Key Facts
- Data covers 24 weeks (2024-01-01 to 2024-06-17), 18 products, 40 stores.
- `sales.promotion_flag` is 1 when a promotion was active that week.
- `inventory.stockout_flag` is 1 when closing_stock was 0 and demand exceeded supply.
- `sales.discount_pct` is a fraction (0.0–1.0), not a percentage.
- Dates are stored as ISO text strings (YYYY-MM-DD).

## Output Format
You MUST respond with ONLY valid JSON in this exact format (no extra text):
{{
  "sql": "<single SELECT statement>",
  "explanation": "<one paragraph plain-English summary of what the query does>"
}}

## Rules
1. Only generate SELECT statements.
2. Only use tables: products, stores, sales, inventory.
3. Always use table aliases and qualify column names to avoid ambiguity.
4. Always include ROUND(..., 2) for monetary values.
5. Use LIMIT 20 unless the question asks for all rows.
6. Never use subqueries that reference sqlite_master or system tables.

## Example
Question: "Which region had the highest total revenue?"
Response:
{{
  "sql": "SELECT region, ROUND(SUM(revenue),2) AS total_revenue FROM sales GROUP BY region ORDER BY total_revenue DESC LIMIT 5",
  "explanation": "This query aggregates all sales revenue by region and ranks them from highest to lowest, letting you see which geographic market generates the most income."
}}
""".strip()


# ---------------------------------------------------------------------------
# Insight generation prompt
# ---------------------------------------------------------------------------
_INSIGHT_PROMPT_TEMPLATE = """
You are a business analyst. Given the question, the SQL query used, and the
first few rows of results, write a concise 2-3 sentence insight summary
suitable for a business stakeholder. Be specific — mention actual numbers
from the results. Do not repeat the question verbatim.

Question: {question}

SQL used:
{sql}

Result sample (up to 5 rows):
{sample}
""".strip()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _call_claude(prompt: str, system: str) -> str:
    """Send a message to Claude and return the text content."""
    import anthropic
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    msg = client.messages.create(
        model=config.LLM_MODEL,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


def _extract_json(text: str) -> dict:
    """Pull the first JSON object out of *text* (handles markdown fences)."""
    # Strip markdown code fences if present
    text = re.sub(r"```(?:json)?", "", text).strip()
    # Find first { ... } block
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ValueError(f"No JSON object found in LLM response: {text[:200]!r}")
    return json.loads(m.group())


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def nl_to_sql(question: str) -> tuple[str, str]:
    """
    Convert a natural-language *question* to (sql, explanation).

    Uses Claude when DEMO_MODE is False, otherwise falls back to demo_mode.
    Raises ValueError if SQL cannot be extracted or generated.
    """
    if config.DEMO_MODE:
        result = demo_mode.match(question)
        if result:
            return result
        return demo_mode.fallback_sql()

    schema = get_schema_ddl()
    system = _SYSTEM_PROMPT_TEMPLATE.format(schema=schema)
    raw = _call_claude(question, system)
    parsed = _extract_json(raw)
    sql = parsed.get("sql", "").strip()
    explanation = parsed.get("explanation", "")
    if not sql:
        raise ValueError("LLM returned empty SQL.")
    return sql, explanation


def generate_insight(question: str, sql: str, rows: list[dict]) -> str:
    """
    Given the executed query and results, ask Claude for a plain-English insight.
    In DEMO_MODE, returns a lightweight template-based summary instead.
    """
    if config.DEMO_MODE or not rows:
        if not rows:
            return "The query returned no results. Try rephrasing your question."
        # Simple template: list top 3 rows
        lines = []
        for i, row in enumerate(rows[:3], 1):
            lines.append(f"{i}. " + ", ".join(f"{k}: {v}" for k, v in row.items()))
        return "Here are the top results:\n" + "\n".join(lines)

    sample = json.dumps(rows[:5], indent=2)
    prompt = _INSIGHT_PROMPT_TEMPLATE.format(
        question=question, sql=sql, sample=sample
    )
    system = "You are a concise, data-driven FMCG business analyst."
    return _call_claude(prompt, system)
