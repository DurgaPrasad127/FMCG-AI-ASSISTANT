"""
frontend/app.py
---------------
Streamlit conversational analytics UI for the FMCG Beverages AI Assistant.

Architecture: Streamlit → FastAPI (/ask) → SQLite

Requires the FastAPI backend running at API_BASE (default: localhost:8000).
Start backend first:
    uvicorn backend.main:app --reload
Then:
    streamlit run frontend/app.py
"""
import sys
import os
import json
import time

import requests
import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
API_BASE = os.environ.get("API_BASE", "http://localhost:8000")

EXAMPLE_QUESTIONS = [
    "Which region had the highest total revenue?",
    "Show me the top 10 products by revenue",
    "What is the impact of promotions on units sold?",
    "Which promotion type drives the most uplift?",
    "Which products had the most stockout weeks?",
    "Show weekly revenue trends over time",
    "How does revenue compare across store formats?",
    "Which brand performed best overall?",
    "What are the worst-performing products?",
    "Give me an inventory summary by product",
    "Break down revenue by product category",
    "Show top products by units sold",
]

CATEGORY_COLORS = {
    "Carbonated": "#6366f1",
    "Water": "#22d3ee",
    "Juice": "#f59e0b",
    "Energy": "#ef4444",
    "Dairy": "#a78bfa",
}

# ---------------------------------------------------------------------------
# Page config — must be first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="FMCG AI Insights Assistant",
    page_icon="🥤",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# CSS — premium dark analytics theme
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ── Root & Base ── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}
.stApp {
    background: linear-gradient(135deg, #0f0f1a 0%, #0d1117 50%, #0a0f1e 100%);
    min-height: 100vh;
}

/* ── Hide default Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.5rem; padding-bottom: 2rem; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #111827 0%, #0d1117 100%);
    border-right: 1px solid rgba(99,102,241,0.2);
}
[data-testid="stSidebar"] .stMarkdown h1,
[data-testid="stSidebar"] .stMarkdown h2,
[data-testid="stSidebar"] .stMarkdown h3 {
    color: #e2e8f0 !important;
}

/* ── Chat containers ── */
.user-bubble {
    background: linear-gradient(135deg, #6366f1, #4f46e5);
    border-radius: 18px 18px 4px 18px;
    padding: 14px 18px;
    margin: 8px 0 8px 15%;
    color: #fff;
    font-size: 0.95rem;
    line-height: 1.6;
    box-shadow: 0 4px 20px rgba(99,102,241,0.3);
    animation: slideInRight 0.3s ease;
}
.assistant-bubble {
    background: linear-gradient(135deg, #1e293b, #162032);
    border: 1px solid rgba(99,102,241,0.25);
    border-radius: 18px 18px 18px 4px;
    padding: 18px 22px;
    margin: 8px 15% 8px 0;
    color: #e2e8f0;
    font-size: 0.95rem;
    line-height: 1.7;
    box-shadow: 0 4px 24px rgba(0,0,0,0.4);
    animation: slideInLeft 0.3s ease;
}
.insight-text {
    color: #94a3b8;
    font-size: 0.9rem;
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px solid rgba(99,102,241,0.15);
}

/* ── Metric cards ── */
.metric-card {
    background: linear-gradient(135deg, #1e293b, #162032);
    border: 1px solid rgba(99,102,241,0.2);
    border-radius: 12px;
    padding: 16px 20px;
    text-align: center;
    transition: all 0.2s ease;
}
.metric-card:hover {
    border-color: rgba(99,102,241,0.5);
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(99,102,241,0.15);
}
.metric-value {
    font-size: 1.8rem;
    font-weight: 700;
    background: linear-gradient(135deg, #6366f1, #a78bfa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.metric-label {
    font-size: 0.75rem;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-top: 4px;
}

/* ── Header ── */
.app-header {
    background: linear-gradient(135deg, rgba(99,102,241,0.15), rgba(167,139,250,0.08));
    border: 1px solid rgba(99,102,241,0.2);
    border-radius: 16px;
    padding: 24px 32px;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    gap: 16px;
}
.app-title {
    font-size: 1.6rem;
    font-weight: 700;
    color: #e2e8f0;
    margin: 0;
}
.app-subtitle {
    font-size: 0.85rem;
    color: #64748b;
    margin: 4px 0 0 0;
}

/* ── Mode badge ── */
.mode-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.05em;
}
.mode-demo {
    background: rgba(245,158,11,0.15);
    border: 1px solid rgba(245,158,11,0.4);
    color: #f59e0b;
}
.mode-llm {
    background: rgba(34,197,94,0.1);
    border: 1px solid rgba(34,197,94,0.4);
    color: #22c55e;
}

/* ── Input area ── */
.stTextInput input {
    background: #1e293b !important;
    border: 1px solid rgba(99,102,241,0.3) !important;
    border-radius: 12px !important;
    color: #e2e8f0 !important;
    font-size: 0.95rem !important;
    padding: 12px 16px !important;
    transition: all 0.2s !important;
}
.stTextInput input:focus {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 2px rgba(99,102,241,0.2) !important;
}

/* ── Buttons ── */
.stButton button {
    background: linear-gradient(135deg, #6366f1, #4f46e5) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    padding: 0.6rem 1.4rem !important;
    transition: all 0.2s !important;
    box-shadow: 0 4px 12px rgba(99,102,241,0.3) !important;
}
.stButton button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(99,102,241,0.4) !important;
}

/* ── Dataframe ── */
.stDataFrame { border-radius: 10px; overflow: hidden; }
[data-testid="stDataFrame"] {
    border: 1px solid rgba(99,102,241,0.2);
    border-radius: 10px;
}

/* ── Code block (SQL viewer) ── */
.stCodeBlock code {
    background: #0d1117 !important;
    color: #a5f3fc !important;
    font-size: 0.82rem !important;
}

/* ── Expander ── */
.streamlit-expanderHeader {
    background: rgba(99,102,241,0.08) !important;
    border: 1px solid rgba(99,102,241,0.2) !important;
    border-radius: 8px !important;
    color: #94a3b8 !important;
    font-size: 0.85rem !important;
}

/* ── Quick question pills ── */
.pill-btn {
    display: inline-block;
    background: rgba(99,102,241,0.1);
    border: 1px solid rgba(99,102,241,0.25);
    border-radius: 20px;
    padding: 5px 14px;
    font-size: 0.78rem;
    color: #94a3b8;
    cursor: pointer;
    margin: 3px 2px;
    transition: all 0.15s;
}
.pill-btn:hover {
    background: rgba(99,102,241,0.25);
    color: #e2e8f0;
    border-color: #6366f1;
}

/* ── Animations ── */
@keyframes slideInRight {
    from { opacity: 0; transform: translateX(20px); }
    to   { opacity: 1; transform: translateX(0); }
}
@keyframes slideInLeft {
    from { opacity: 0; transform: translateX(-20px); }
    to   { opacity: 1; transform: translateX(0); }
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}
.thinking-dot {
    display: inline-block;
    width: 8px; height: 8px;
    border-radius: 50%;
    background: #6366f1;
    animation: pulse 1.2s ease infinite;
    margin: 0 2px;
}
.thinking-dot:nth-child(2) { animation-delay: 0.2s; }
.thinking-dot:nth-child(3) { animation-delay: 0.4s; }

/* ── Divider ── */
hr { border-color: rgba(99,102,241,0.15) !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #0d1117; }
::-webkit-scrollbar-thumb { background: rgba(99,102,241,0.4); border-radius: 3px; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "health" not in st.session_state:
    st.session_state.health = None
if "pending_question" not in st.session_state:
    st.session_state.pending_question = ""


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------
@st.cache_data(ttl=30)
def fetch_health():
    try:
        r = requests.get(f"{API_BASE}/health", timeout=5)
        return r.json() if r.ok else None
    except Exception:
        return None


def call_ask(question: str) -> dict | None:
    try:
        r = requests.post(
            f"{API_BASE}/ask",
            json={"question": question},
            timeout=60,
        )
        if r.ok:
            return r.json()
        return {"error": r.json().get("detail", "Unknown error")}
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot reach the API server. Is the backend running?"}
    except Exception as e:
        return {"error": str(e)}


def fmt_number(n) -> str:
    if isinstance(n, float):
        return f"{n:,.2f}"
    if isinstance(n, int):
        return f"{n:,}"
    return str(n)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 🥤 FMCG AI Assistant")
    st.markdown("---")

    # Health / status
    health = fetch_health()
    if health:
        mode_class = "mode-llm" if not health.get("demo_mode") else "mode-demo"
        mode_icon = "🤖" if not health.get("demo_mode") else "⚡"
        mode_label = f"LLM Mode ({health.get('llm_model','')})" if not health.get("demo_mode") else "Demo Mode"
        st.markdown(
            f'<span class="mode-badge {mode_class}">{mode_icon} {mode_label}</span>',
            unsafe_allow_html=True,
        )
        st.markdown("")

        # DB stats as metric cards
        counts = health.get("row_counts", {})
        for tbl, count in counts.items():
            st.markdown(
                f'<div class="metric-card">'
                f'<div class="metric-value">{count:,}</div>'
                f'<div class="metric-label">{tbl}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            st.markdown("")
    else:
        st.error("⚠️ Backend offline")
        st.markdown("Start the backend:\n```\nuvicorn backend.main:app --reload\n```")

    st.markdown("---")
    st.markdown("### 💡 Try asking...")

    for q in EXAMPLE_QUESTIONS:
        if st.button(q, key=f"pill_{hash(q)}", use_container_width=True):
            st.session_state.pending_question = q

    st.markdown("---")
    st.markdown(
        '<p style="font-size:0.75rem;color:#475569;text-align:center;">'
        'FMCG Beverages AI Assistant<br>'
        '18 SKUs · 40 Stores · 24 Weeks'
        '</p>',
        unsafe_allow_html=True,
    )

    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


# ---------------------------------------------------------------------------
# Main area — Header
# ---------------------------------------------------------------------------
st.markdown(
    '<div class="app-header">'
    '<span style="font-size:2.5rem;">🥤</span>'
    '<div>'
    '<h1 class="app-title">FMCG Beverages AI Insights Assistant</h1>'
    '<p class="app-subtitle">'
    'Ask plain-English questions about sales, inventory, promotions, and store performance'
    '</p>'
    '</div>'
    '</div>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Chat history
# ---------------------------------------------------------------------------
chat_container = st.container()

with chat_container:
    if not st.session_state.messages:
        st.markdown(
            '<div style="text-align:center;padding:60px 20px;">'
            '<div style="font-size:3rem;margin-bottom:16px;">💬</div>'
            '<h3 style="color:#475569;font-weight:500;">Ask your first question</h3>'
            '<p style="color:#334155;font-size:0.9rem;">'
            'Try: <em>"Which region had the highest revenue?"</em> or pick from the sidebar.'
            '</p>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                st.markdown(
                    f'<div class="user-bubble">🧑‍💼 {msg["content"]}</div>',
                    unsafe_allow_html=True,
                )
            else:
                data = msg["data"]
                if "error" in data:
                    st.markdown(
                        f'<div class="assistant-bubble">'
                        f'<strong style="color:#ef4444;">⚠️ Error</strong><br>'
                        f'<span class="insight-text">{data["error"]}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    insight_html = data.get("insight", "").replace("\n", "<br>")
                    elapsed = data.get("elapsed_ms", 0)
                    row_count = data.get("row_count", 0)

                    st.markdown(
                        f'<div class="assistant-bubble">'
                        f'<strong style="color:#a78bfa;">🤖 Assistant</strong> '
                        f'<span style="font-size:0.75rem;color:#475569;">({elapsed}ms · {row_count} rows)</span>'
                        f'<div class="insight-text">{insight_html}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                    # Data table
                    rows = data.get("rows", [])
                    if rows:
                        df = pd.DataFrame(rows)
                        # Format numeric columns
                        for col in df.select_dtypes(include=["float64"]).columns:
                            df[col] = df[col].apply(lambda x: round(x, 2))
                        st.dataframe(
                            df,
                            use_container_width=True,
                            hide_index=True,
                        )

                    # SQL viewer
                    with st.expander("🔍 View generated SQL", expanded=False):
                        st.code(data.get("sql", ""), language="sql")

                    st.markdown("")


# ---------------------------------------------------------------------------
# Input row — fixed at bottom
# ---------------------------------------------------------------------------
st.markdown("---")
col_input, col_btn = st.columns([6, 1])

with col_input:
    default_val = st.session_state.pending_question
    question = st.text_input(
        "Ask a question",
        value=default_val,
        placeholder="e.g. Which products had the most stockouts?",
        label_visibility="collapsed",
        key="question_input",
    )

with col_btn:
    submit = st.button("Ask ✨", use_container_width=True)

# Clear pending question after it's been loaded
if st.session_state.pending_question:
    st.session_state.pending_question = ""

# ---------------------------------------------------------------------------
# Handle submission
# ---------------------------------------------------------------------------
if submit and question.strip():
    st.session_state.messages.append({"role": "user", "content": question.strip()})

    with st.spinner(""):
        st.markdown(
            '<div style="text-align:center;padding:8px;">'
            '<span class="thinking-dot"></span>'
            '<span class="thinking-dot"></span>'
            '<span class="thinking-dot"></span>'
            '</div>',
            unsafe_allow_html=True,
        )
        result = call_ask(question.strip())

    st.session_state.messages.append({"role": "assistant", "data": result})
    st.rerun()
