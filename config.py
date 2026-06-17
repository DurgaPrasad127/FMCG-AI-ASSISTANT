"""
config.py — centralised environment configuration.

Design note: all secrets/config come from environment variables (never
hardcoded), so the same code runs locally, in Docker, or on Render/Railway/
Streamlit Cloud just by setting env vars / secrets differently.
"""
import os

# --- LLM provider ---
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "claude-sonnet-4-6")

# If no API key is configured, the assistant runs in DEMO_MODE: a
# deterministic rule-based intent matcher is used instead of calling an LLM.
# This keeps the prototype fully runnable/demoable (e.g. for grading) with
# zero external dependencies or cost, while the real LLM-backed NL->SQL path
# is fully implemented in llm.py and activates automatically once a key is set.
DEMO_MODE = len(ANTHROPIC_API_KEY.strip()) == 0

# --- Database ---
# DB_BACKEND: "sqlite" (default, zero-setup) or "postgres" (production).
DB_BACKEND = os.environ.get("DB_BACKEND", "sqlite")
SQLITE_PATH = os.environ.get("SQLITE_PATH", os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "fmcg.db"))
POSTGRES_DSN = os.environ.get("POSTGRES_DSN", "")

# --- App ---
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
MAX_QUERY_ROWS = int(os.environ.get("MAX_QUERY_ROWS", "500"))  # guardrail: cap result size
ALLOWED_TABLES = {"products", "stores", "sales", "inventory"}
