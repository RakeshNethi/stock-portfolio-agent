"""Market data collection node.

Fetches current quotes for all portfolio tickers and
compiles a market overview (indices + VIX).
"""

from __future__ import annotations

from datetime import datetime

from src.agent.state import AgentState
from src.data.alpha_vantage import AlphaVantageClient
from src.utils.logging import get_logger

log = get_logger(__name__)

# Index ETFs used as proxies for market overview
INDEX_TICKERS = {
    "SPY": "S&P 500",
    "QQQ": "NASDAQ",
    "DIA": "Dow Jones",
}


def fetch_market_data(state: AgentState) -> dict:
    """Fetch current quotes for all portfolio tickers + market indices.

    This node:
    1. Gets the latest quote for each ticker in the portfolio + watchlist
    2. Fetches broad market indices (SPY, QQQ, DIA)
    3. Stores everything in state for downstream nodes

    Args:
        state: Current agent state with portfolio loaded.

    Returns:
        State update dict with quotes and market_overview.
    """
    tickers = state.get("all_tickers", [])
    log.info("fetch_market_data_start", ticker_count=len(tickers))

    client = AlphaVantageClient()
    quotes = {}
    errors = []

    try:
        # Fetch quotes for portfolio holdings + watchlist
        for ticker in tickers:
            try:
                quote = client.get_quote(ticker)
                quotes[ticker] = quote.model_dump()
                log.info(
                    "quote_fetched",
                    ticker=ticker,
                    price=quote.price,
                    change_pct=quote.change_percent,
                )
            except Exception as e:
                log.error("quote_fetch_error", ticker=ticker, error=str(e))
                errors.append({"ticker": ticker, "error": str(e)})

        # Fetch market indices
        market_quotes = {}
        for idx_ticker, idx_name in INDEX_TICKERS.items():
            if idx_ticker not in quotes:  # Don't double-fetch if in portfolio
                try:
                    idx_quote = client.get_quote(idx_ticker)
                    market_quotes[idx_name] = idx_quote.model_dump()
                except Exception as e:
                    log.error("index_fetch_error", index=idx_name, error=str(e))

        market_overview = {
            "indices": market_quotes,
            "market_status": "closed" if datetime.now().hour >= 16 else "open",
            "timestamp": datetime.now().isoformat(),
            "errors": errors,
        }

    finally:
        client.close()

    log.info(
        "fetch_market_data_complete",
        quotes_fetched=len(quotes),
        errors=len(errors),
    )

    return {
        "quotes": quotes,
        "market_overview": market_overview,
        "audit_log": [
            {
                "timestamp": datetime.now().isoformat(),
                "agent": "MarketDataCollector",
                "action": "fetch_market_data",
                "detail": f"Fetched {len(quotes)} quotes, {len(errors)} errors",
            }
        ],
    }
