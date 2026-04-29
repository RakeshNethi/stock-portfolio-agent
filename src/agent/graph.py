"""LangGraph workflow definition.

Assembles all agent nodes into a directed graph that:
1. Loads the portfolio from config
2. Fetches market data (quotes)
3. Runs technical analysis, earnings check, and news in parallel
4. Synthesizes everything into a briefing via LLM
5. Checks quality (retry once if needed)
6. Sends notifications
"""

from __future__ import annotations

import uuid
from datetime import datetime

from langgraph.graph import END, StateGraph

from src.agent.nodes.earnings_tracker import check_earnings
from src.agent.nodes.market_data import fetch_market_data
from src.agent.nodes.news_sentiment import fetch_news_sentiment
from src.agent.nodes.notifier import send_notifications
from src.agent.nodes.synthesizer import synthesize_briefing
from src.agent.nodes.technical_analysis import run_technical_analysis
from src.agent.state import AgentState
from src.utils.config import load_portfolio, get_run_type
from src.utils.logging import get_logger

log = get_logger(__name__)


def load_portfolio_node(state: AgentState) -> dict:
    """Load portfolio from YAML config and populate initial state."""
    log.info("load_portfolio_start")

    portfolio = load_portfolio()
    run_type = state.get("run_type") or get_run_type()

    log.info(
        "load_portfolio_complete",
        accounts=len(portfolio.accounts),
        holdings=len(portfolio.all_holdings),
        tickers=len(portfolio.all_tickers),
        run_type=run_type,
    )

    return {
        "run_id": state.get("run_id") or str(uuid.uuid4()),
        "run_type": run_type,
        "timestamp": datetime.now().isoformat(),
        "portfolio": portfolio.model_dump(),
        "all_tickers": portfolio.all_tickers,
        "audit_log": [
            {
                "timestamp": datetime.now().isoformat(),
                "agent": "PortfolioLoader",
                "action": "load_portfolio",
                "detail": f"Loaded {len(portfolio.all_holdings)} holdings across {len(portfolio.accounts)} accounts",
            }
        ],
    }


def quality_check(state: AgentState) -> str:
    """Route based on briefing quality. Returns next node name."""
    quality = state.get("quality_score", 0.0)
    retry_count = state.get("retry_count", 0)

    if quality >= 0.5:
        log.info("quality_check_pass", score=quality)
        return "send_notifications"
    elif retry_count < 1:
        log.warning("quality_check_retry", score=quality, retry=retry_count)
        return "synthesize_briefing"
    else:
        log.error("quality_check_fail", score=quality, retries_exhausted=True)
        return "send_notifications"  # Send whatever we have


def increment_retry(state: AgentState) -> dict:
    """Increment retry counter before re-synthesis."""
    return {"retry_count": (state.get("retry_count", 0) + 1)}


def build_graph() -> StateGraph:
    """Build and compile the LangGraph workflow.

    Graph structure:
        load_portfolio → fetch_market_data → [technical_analysis, earnings, news]
        → synthesize_briefing → quality_check → send_notifications

    Returns:
        Compiled LangGraph StateGraph.
    """
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("load_portfolio", load_portfolio_node)
    workflow.add_node("fetch_market_data", fetch_market_data)
    workflow.add_node("run_technical_analysis", run_technical_analysis)
    workflow.add_node("check_earnings", check_earnings)
    workflow.add_node("fetch_news_sentiment", fetch_news_sentiment)
    workflow.add_node("synthesize_briefing", synthesize_briefing)
    workflow.add_node("send_notifications", send_notifications)
    workflow.add_node("increment_retry", increment_retry)

    # Define edges
    workflow.set_entry_point("load_portfolio")
    workflow.add_edge("load_portfolio", "fetch_market_data")

    # After fetching market data, run analysis nodes sequentially
    # (to conserve API rate limits on free tier)
    workflow.add_edge("fetch_market_data", "run_technical_analysis")
    workflow.add_edge("run_technical_analysis", "check_earnings")
    workflow.add_edge("check_earnings", "fetch_news_sentiment")

    # After all analysis, synthesize
    workflow.add_edge("fetch_news_sentiment", "synthesize_briefing")

    # Quality gate with conditional routing
    workflow.add_conditional_edges(
        "synthesize_briefing",
        quality_check,
        {
            "send_notifications": "send_notifications",
            "synthesize_briefing": "increment_retry",
        },
    )
    workflow.add_edge("increment_retry", "synthesize_briefing")

    # End after notifications
    workflow.add_edge("send_notifications", END)

    return workflow.compile()


# Module-level compiled graph
graph = build_graph()
