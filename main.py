"""
backend/main.py
---------------
FastAPI application — the central API layer between the Streamlit frontend
and the SQLite database.

Endpoints:
  GET  /health          Liveness + mode check
  GET  /schema          DB schema DDL (for debugging / transparency)
  GET  /tables/{table}  Preview first N rows of a core table
  POST /ask             Main NL→SQL→insight pipeline
"""
import logging
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import config
from backend.db import run_query, table_row_counts, get_schema_ddl
from backend.llm import nl_to_sql, generate_insight
from backend.query_guard import validate, QueryGuardError

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
logging.basicConfig(level=getattr(logging, config.LOG_LEVEL, logging.INFO))
log = logging.getLogger("fmcg.api")

app = FastAPI(
    title="FMCG Beverages AI Insights Assistant",
    description=(
        "Conversational analytics API. POST a plain-English question to /ask "
        "and receive SQL, results, and a business insight summary."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------
class AskRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        max_length=500,
        example="Which region had the highest revenue?",
    )


class AskResponse(BaseModel):
    question: str
    sql: str
    rows: list[dict]
    insight: str
    row_count: int
    demo_mode: bool
    elapsed_ms: int


# ---------------------------------------------------------------------------
# Middleware — request timing
# ---------------------------------------------------------------------------
@app.middleware("http")
async def add_timing(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    elapsed = round((time.time() - start) * 1000)
    response.headers["X-Elapsed-Ms"] = str(elapsed)
    return response


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/health", tags=["Ops"])
def health():
    """Liveness check — also reports mode and DB row counts."""
    try:
        counts = table_row_counts()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"DB unavailable: {e}")
    return {
        "status": "ok",
        "demo_mode": config.DEMO_MODE,
        "llm_model": config.LLM_MODEL,
        "db_backend": config.DB_BACKEND,
        "row_counts": counts,
    }


@app.get("/schema", tags=["Debug"])
def schema():
    """Return the SQLite CREATE TABLE DDL for all core tables."""
    try:
        ddl = get_schema_ddl()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"schema": ddl}


@app.get("/tables/{table}", tags=["Debug"])
def preview_table(table: str, limit: int = 5):
    """Preview the first *limit* rows of a core table."""
    if table not in config.ALLOWED_TABLES:
        raise HTTPException(
            status_code=400,
            detail=f"Table '{table}' not in allowed set: {config.ALLOWED_TABLES}",
        )
    try:
        rows = run_query(f"SELECT * FROM {table} LIMIT ?", (limit,))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"table": table, "rows": rows}


@app.post("/ask", response_model=AskResponse, tags=["AI"])
def ask(req: AskRequest):
    """
    Main NL→SQL→insight endpoint.

    1. Convert question to SQL via LLM (or demo_mode).
    2. Validate SQL with query_guard.
    3. Execute SQL against SQLite.
    4. Generate a plain-English insight from the results.
    5. Return everything to the caller.
    """
    t0 = time.time()
    log.info("Question: %s", req.question)

    # Step 1 — NL→SQL
    try:
        sql, explanation = nl_to_sql(req.question)
        log.info("Generated SQL: %s", sql)
    except Exception as e:
        log.error("NL→SQL failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Query generation failed: {e}")

    # Step 2 — Guard
    try:
        sql = validate(sql)
    except QueryGuardError as e:
        log.warning("QueryGuard blocked SQL: %s | Reason: %s", sql, e)
        raise HTTPException(status_code=400, detail=f"SQL safety check failed: {e}")

    # Step 3 — Execute
    try:
        rows = run_query(sql)
    except Exception as e:
        log.error("DB query failed: %s | SQL: %s", e, sql)
        raise HTTPException(status_code=500, detail=f"Query execution failed: {e}")

    # Step 4 — Insight
    try:
        insight = generate_insight(req.question, sql, rows)
    except Exception as e:
        log.warning("Insight generation failed (non-fatal): %s", e)
        insight = explanation  # fall back to SQL explanation

    elapsed_ms = round((time.time() - t0) * 1000)
    log.info("Answered in %dms | %d rows returned", elapsed_ms, len(rows))

    return AskResponse(
        question=req.question,
        sql=sql,
        rows=rows,
        insight=insight,
        row_count=len(rows),
        demo_mode=config.DEMO_MODE,
        elapsed_ms=elapsed_ms,
    )
