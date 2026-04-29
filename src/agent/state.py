"""Agent state definition.

The shared state object that flows through every node in the
LangGraph workflow. Uses TypedDict with Annotated fields for
LangGraph's state management.
"""

from __future__ import annotations

from typing import Annotated, Any

from langgraph.graph import add_messages
from typing_extensions import TypedDict


def _merge_lists(existing: list, new: list) -> list:
    """Reducer that appends new items to existing list."""
    return existing + new


def _replace(existing: Any, new: Any) -> Any:
    """Reducer that replaces the existing value with the new one."""
    return new


class AgentState(TypedDict, total=False):
    """State shared across all LangGraph nodes.

    Each key uses a reducer annotation to control how updates
    from parallel or sequential nodes are merged.
    """

    # ── Run context ──────────────────────────────────────────
    run_id: Annotated[str, _replace]
    run_type: Annotated[str, _replace]          # "morning" or "evening"
    timestamp: Annotated[str, _replace]

    # ── Portfolio (set by load_portfolio node) ───────────────
    portfolio: Annotated[dict, _replace]         # Serialized Portfolio model
    all_tickers: Annotated[list[str], _replace]  # Deduplicated ticker list

    # ── Market data (set by fetch_market_data node) ──────────
    quotes: Annotated[dict[str, dict], _replace]  # ticker → Quote dict
    market_overview: Annotated[dict, _replace]

    # ── Technical analysis (set by run_technical_analysis) ───
    technical_signals: Annotated[dict[str, dict], _replace]  # ticker → TechnicalSummary dict

    # ── Earnings (set by check_earnings node) ────────────────
    upcoming_earnings: Annotated[list[dict], _merge_lists]
    recent_surprises: Annotated[list[dict], _merge_lists]

    # ── News & sentiment (set by fetch_news_sentiment) ───────
    news_headlines: Annotated[list[dict], _merge_lists]
    sentiment_scores: Annotated[dict[str, float], _replace]

    # ── LLM output (set by synthesize_briefing node) ────────
    briefing: Annotated[dict, _replace]          # Serialized DailyBriefing
    recommendations: Annotated[list[dict], _replace]

    # ── Quality gate ─────────────────────────────────────────
    quality_score: Annotated[float, _replace]
    retry_count: Annotated[int, _replace]

    # ── Audit trail ──────────────────────────────────────────
    audit_log: Annotated[list[dict], _merge_lists]
