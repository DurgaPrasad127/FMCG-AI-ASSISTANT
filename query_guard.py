"""
backend/query_guard.py
----------------------
Read-only SQL guardrail. Validates LLM-generated SQL before execution:
- Only SELECT statements allowed (no DML / DDL).
- Only tables in ALLOWED_TABLES may be referenced.
- No subquery tricks to access sqlite_master or system tables.
"""
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# Patterns for dangerous statement types
_DANGEROUS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|REPLACE|TRUNCATE|ATTACH|DETACH|PRAGMA)\b",
    re.IGNORECASE,
)

# System / metadata tables that must never be touched
_SYSTEM_TABLES = re.compile(
    r"\b(sqlite_master|sqlite_sequence|information_schema)\b",
    re.IGNORECASE,
)


class QueryGuardError(ValueError):
    """Raised when a generated SQL query fails the safety checks."""


def validate(sql: str) -> str:
    """
    Validate *sql* and return it stripped if safe, or raise QueryGuardError.
    """
    sql = sql.strip().rstrip(";")

    if not sql.upper().lstrip().startswith("SELECT"):
        raise QueryGuardError(
            "Only SELECT statements are permitted. "
            f"Received statement starting with: {sql[:40]!r}"
        )

    if _DANGEROUS.search(sql):
        match = _DANGEROUS.search(sql)
        raise QueryGuardError(
            f"Forbidden keyword detected in SQL: {match.group()!r}"
        )

    if _SYSTEM_TABLES.search(sql):
        raise QueryGuardError("Access to system tables is not permitted.")

    # Check all table references are in ALLOWED_TABLES
    # Extract identifiers that follow FROM / JOIN keywords
    table_refs = re.findall(
        r'\bFROM\s+(\w+)|\bJOIN\s+(\w+)', sql, re.IGNORECASE
    )
    referenced = {(a or b).lower() for a, b in table_refs}
    disallowed = referenced - {t.lower() for t in config.ALLOWED_TABLES}
    if disallowed:
        raise QueryGuardError(
            f"Query references disallowed table(s): {disallowed}. "
            f"Allowed: {config.ALLOWED_TABLES}"
        )

    return sql
