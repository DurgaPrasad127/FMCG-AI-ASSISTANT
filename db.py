"""
backend/db.py
-------------
SQLite connection helper. Provides a single entry point for executing
read-only SQL queries against fmcg.db with row-count guardrails.
"""
import sqlite3
import sys
import os

# Allow imports from project root (config.py lives there)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.SQLITE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def run_query(sql: str, params: tuple = ()) -> list[dict]:
    """Execute *sql* (read-only) and return up to MAX_QUERY_ROWS rows as dicts."""
    conn = _connect()
    try:
        cur = conn.execute(sql, params)
        rows = cur.fetchmany(config.MAX_QUERY_ROWS)
        return [dict(r) for r in rows]
    finally:
        conn.close()


def table_row_counts() -> dict[str, int]:
    """Return row counts for all four core tables."""
    conn = _connect()
    try:
        counts = {}
        for tbl in config.ALLOWED_TABLES:
            counts[tbl] = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        return counts
    finally:
        conn.close()


def get_schema_ddl() -> str:
    """Return the CREATE TABLE DDL for all allowed tables."""
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name IN "
            "('products','stores','sales','inventory') ORDER BY name"
        ).fetchall()
        return "\n\n".join(r[0] for r in rows if r[0])
    finally:
        conn.close()
