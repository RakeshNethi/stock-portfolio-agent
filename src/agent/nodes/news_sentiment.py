"""News and sentiment analysis node.

Fetches recent news headlines and performs sentiment scoring
for portfolio holdings using the Finnhub API.

This is a Phase 2 implementation — currently uses a placeholder.
"""

from __future__ import annotations

from datetime import datetime

from src.agent.state import AgentState
from src.utils.logging import get_logger

log = get_logger(__name__)


def fetch_news_sentiment(state: AgentState) -> dict:
    """Fetch news headlines and sentiment scores for portfolio holdings.

    Phase 1: Returns placeholder data.
    Phase 2: Will integrate with Finnhub API to fetch:
      - Recent company news (last 24-48 hours)
      - Sentiment analysis scores per ticker

    Args:
        state: Agent state with portfolio loaded.

    Returns:
        State update with news_headlines and sentiment_scores.
    """
    portfolio = state.get("portfolio", {})
    holding_tickers = set()
    for acct in portfolio.get("accounts", []):
        for h in acct.get("holdings", []):
            holding_tickers.add(h["ticker"])

    log.info("fetch_news_start", ticker_count=len(holding_tickers))

    from src.data.finnhub_client import FinnhubClient
    client = FinnhubClient()
    tickers = list(holding_tickers)
    
    news_headlines = client.get_company_news(tickers, days=2)
    sentiment_scores = client.get_sentiment(tickers)

    log.info(
        "fetch_news_complete",
        headlines=len(news_headlines),
        tickers_scored=len(sentiment_scores),
    )

    return {
        "news_headlines": news_headlines,
        "sentiment_scores": sentiment_scores,
        "audit_log": [
            {
                "timestamp": datetime.now().isoformat(),
                "agent": "NewsSentimentAnalyzer",
                "action": "fetch_news_sentiment",
                "detail": f"Fetched news: {len(news_headlines)} headlines",
            }
        ],
    }
