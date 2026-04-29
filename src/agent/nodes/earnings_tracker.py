"""Earnings tracker node.

Checks for upcoming earnings events and recent earnings surprises
for portfolio holdings using the Financial Modeling Prep API.

This is a Phase 2 implementation — currently uses a placeholder
that returns empty data. Will be connected to the FMP API client.
"""

from __future__ import annotations

from datetime import datetime

from src.agent.state import AgentState
from src.utils.logging import get_logger

log = get_logger(__name__)


def check_earnings(state: AgentState) -> dict:
    """Check for upcoming and recent earnings events.

    Phase 1: Returns placeholder data.
    Phase 2: Will integrate with Financial Modeling Prep API to fetch:
      - Earnings calendar for holdings (next 7 days)
      - Recent earnings surprises (last 7 days)

    Args:
        state: Agent state with portfolio loaded.

    Returns:
        State update with upcoming_earnings and recent_surprises.
    """
    portfolio = state.get("portfolio", {})
    holding_tickers = set()
    for acct in portfolio.get("accounts", []):
        for h in acct.get("holdings", []):
            holding_tickers.add(h["ticker"])

    log.info("check_earnings_start", ticker_count=len(holding_tickers))

    from src.data.fmp_client import FMPClient
    client = FMPClient()
    tickers = list(holding_tickers)
    
    upcoming_earnings = client.get_earnings_calendar(tickers, lookahead_days=7)
    recent_surprises = client.get_recent_surprises(tickers, lookback_days=7)



    log.info(
        "check_earnings_complete",
        upcoming=len(upcoming_earnings),
        surprises=len(recent_surprises),
    )

    return {
        "upcoming_earnings": upcoming_earnings,
        "recent_surprises": recent_surprises,
        "audit_log": [
            {
                "timestamp": datetime.now().isoformat(),
                "agent": "EarningsTracker",
                "action": "check_earnings",
                "detail": f"Checked earnings: {len(upcoming_earnings)} upcoming, {len(recent_surprises)} surprises",
            }
        ],
    }
