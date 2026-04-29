"""Tests for portfolio and market data models."""

from __future__ import annotations

from src.models.market import Quote, SignalStrength, TechnicalIndicator, TechnicalSummary
from src.models.portfolio import Account, Holding, Portfolio


class TestPortfolioModels:
    """Test suite for portfolio data models."""

    def test_holding_total_cost(self):
        h = Holding(ticker="AAPL", shares=50, cost_basis=178.25)
        assert h.total_cost == 50 * 178.25

    def test_portfolio_all_tickers(self):
        portfolio = Portfolio(
            accounts=[
                Account(
                    name="Test",
                    broker="test",
                    holdings=[
                        Holding(ticker="AAPL", shares=10, cost_basis=150),
                        Holding(ticker="NVDA", shares=5, cost_basis=400),
                    ],
                )
            ],
            watchlist=["TSLA", "AMD"],
        )
        tickers = portfolio.all_tickers
        assert "AAPL" in tickers
        assert "NVDA" in tickers
        assert "TSLA" in tickers
        assert "AMD" in tickers
        assert len(tickers) == 4

    def test_portfolio_holding_tickers_excludes_watchlist(self):
        portfolio = Portfolio(
            accounts=[
                Account(
                    name="Test",
                    broker="test",
                    holdings=[Holding(ticker="AAPL", shares=10, cost_basis=150)],
                )
            ],
            watchlist=["TSLA"],
        )
        assert "AAPL" in portfolio.holding_tickers
        assert "TSLA" not in portfolio.holding_tickers

    def test_portfolio_total_invested(self):
        portfolio = Portfolio(
            accounts=[
                Account(
                    name="Test",
                    broker="test",
                    holdings=[
                        Holding(ticker="AAPL", shares=10, cost_basis=150),
                        Holding(ticker="NVDA", shares=5, cost_basis=400),
                    ],
                )
            ],
        )
        assert portfolio.total_invested == (10 * 150) + (5 * 400)

    def test_get_holding_merges_across_accounts(self):
        portfolio = Portfolio(
            accounts=[
                Account(
                    name="Account 1",
                    broker="broker1",
                    holdings=[Holding(ticker="AAPL", shares=10, cost_basis=150)],
                ),
                Account(
                    name="Account 2",
                    broker="broker2",
                    holdings=[Holding(ticker="AAPL", shares=20, cost_basis=180)],
                ),
            ],
        )
        merged = portfolio.get_holding("AAPL")
        assert merged is not None
        assert merged.shares == 30
        # Weighted average: (10*150 + 20*180) / 30 = 5100/30 = 170
        assert merged.cost_basis == 170.0

    def test_get_holding_returns_none_for_missing(self):
        portfolio = Portfolio(accounts=[])
        assert portfolio.get_holding("XYZ") is None


class TestMarketModels:
    """Test suite for market data models."""

    def test_quote_creation(self):
        q = Quote(ticker="AAPL", price=198.50, change=1.25, change_percent=0.63)
        assert q.ticker == "AAPL"
        assert q.price == 198.50

    def test_technical_summary_signal_counts(self):
        summary = TechnicalSummary(
            ticker="AAPL",
            indicators=[
                TechnicalIndicator(ticker="AAPL", indicator="rsi", value=55, signal=SignalStrength.HOLD),
                TechnicalIndicator(ticker="AAPL", indicator="macd", value=0.5, signal=SignalStrength.BUY),
                TechnicalIndicator(ticker="AAPL", indicator="sma_50", value=180, signal=SignalStrength.BUY),
            ],
        )
        counts = summary.signal_counts
        assert counts["buy"] == 2
        assert counts["hold"] == 1
