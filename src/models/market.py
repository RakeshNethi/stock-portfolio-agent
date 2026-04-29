"""Market data models.

Defines structures for stock quotes, OHLCV data, market indices,
and technical analysis indicators returned by data APIs.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field


class Quote(BaseModel):
    """Current or latest stock quote."""

    ticker: str
    price: float = Field(..., description="Current/last price in USD")
    change: float = Field(0.0, description="Price change from previous close")
    change_percent: float = Field(0.0, description="Percentage change from previous close")
    volume: int = Field(0, description="Trading volume")
    avg_volume: int | None = Field(None, description="Average daily volume")
    high: float | None = None
    low: float | None = None
    open: float | None = None
    previous_close: float | None = None
    timestamp: datetime | None = None


class OHLCV(BaseModel):
    """A single candlestick / price bar."""

    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int


class SignalStrength(str, Enum):
    """Strength of a technical signal."""

    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


class TechnicalIndicator(BaseModel):
    """A computed technical indicator for a stock."""

    ticker: str
    indicator: str = Field(..., description="Indicator name (e.g. rsi_14, macd, sma_50)")
    value: float | dict = Field(..., description="Current indicator value or dict of values")
    signal: SignalStrength = Field(SignalStrength.HOLD, description="Interpreted trading signal")
    detail: str = Field("", description="Human-readable interpretation")


class TechnicalSummary(BaseModel):
    """Aggregated technical analysis for a single stock."""

    ticker: str
    indicators: list[TechnicalIndicator] = Field(default_factory=list)
    overall_signal: SignalStrength = SignalStrength.HOLD
    summary: str = ""

    @property
    def signal_counts(self) -> dict[str, int]:
        """Count of each signal type across all indicators."""
        counts: dict[str, int] = {}
        for ind in self.indicators:
            key = ind.signal.value
            counts[key] = counts.get(key, 0) + 1
        return counts


class MarketOverview(BaseModel):
    """Broad market summary — indices, volatility, treasuries."""

    sp500: Quote | None = None
    nasdaq: Quote | None = None
    dow: Quote | None = None
    vix: float | None = Field(None, description="CBOE Volatility Index")
    treasury_10y: float | None = Field(None, description="10-Year Treasury yield")
    market_status: str = Field("unknown", description="open, closed, pre-market, after-hours")
    timestamp: datetime | None = None
