"""Portfolio data models.

Defines the structure for brokerage accounts, individual holdings,
and the aggregate portfolio loaded from config/portfolio.yaml.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Holding(BaseModel):
    """A single stock position within an account."""

    ticker: str = Field(..., description="Stock ticker symbol (e.g. AAPL)")
    shares: float = Field(..., ge=0, description="Number of shares held")
    cost_basis: float = Field(..., ge=0, description="Average cost per share in USD")

    @property
    def total_cost(self) -> float:
        """Total amount invested in this position."""
        return self.shares * self.cost_basis


class Account(BaseModel):
    """A brokerage account containing multiple holdings."""

    name: str = Field(..., description="Human-readable account name")
    broker: str = Field(..., description="Broker name (e.g. robinhood, fidelity)")
    holdings: list[Holding] = Field(default_factory=list)


class Portfolio(BaseModel):
    """The complete portfolio across all accounts, plus a watchlist."""

    accounts: list[Account] = Field(default_factory=list)
    watchlist: list[str] = Field(default_factory=list, description="Tickers to track but not owned")

    @property
    def all_holdings(self) -> list[Holding]:
        """Flat list of all holdings across all accounts."""
        return [h for acct in self.accounts for h in acct.holdings]

    @property
    def all_tickers(self) -> list[str]:
        """Unique tickers from holdings + watchlist."""
        holding_tickers = {h.ticker for h in self.all_holdings}
        watchlist_tickers = set(self.watchlist)
        return sorted(holding_tickers | watchlist_tickers)

    @property
    def holding_tickers(self) -> list[str]:
        """Unique tickers from holdings only (positions you own)."""
        return sorted({h.ticker for h in self.all_holdings})

    @property
    def total_invested(self) -> float:
        """Total cost basis across all holdings."""
        return sum(h.total_cost for h in self.all_holdings)

    def get_holding(self, ticker: str) -> Holding | None:
        """Get aggregate holding for a ticker (merged across accounts)."""
        matches = [h for h in self.all_holdings if h.ticker == ticker]
        if not matches:
            return None
        total_shares = sum(h.shares for h in matches)
        weighted_cost = sum(h.shares * h.cost_basis for h in matches) / total_shares
        return Holding(ticker=ticker, shares=total_shares, cost_basis=weighted_cost)
