"""Earnings data models.

Structures for tracking upcoming earnings events, recent results,
and earnings surprise data.
"""

from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class EarningsTime(str, Enum):
    """When earnings are reported relative to market hours."""

    BEFORE_OPEN = "bmo"      # Before Market Open
    AFTER_CLOSE = "amc"      # After Market Close
    DURING_HOURS = "dmh"     # During Market Hours
    UNKNOWN = "unknown"


class EarningsEvent(BaseModel):
    """An upcoming or recent earnings release."""

    ticker: str
    company_name: str = ""
    report_date: date
    report_time: EarningsTime = EarningsTime.UNKNOWN
    eps_estimate: float | None = Field(None, description="Consensus EPS estimate")
    revenue_estimate: float | None = Field(None, description="Consensus revenue estimate in USD")

    @property
    def is_upcoming(self) -> bool:
        """Whether this earnings event is in the future."""
        return self.report_date >= date.today()


class EarningsSurprise(BaseModel):
    """Actual vs expected earnings result."""

    ticker: str
    company_name: str = ""
    report_date: date
    eps_actual: float | None = None
    eps_estimate: float | None = None
    revenue_actual: float | None = None
    revenue_estimate: float | None = None

    @property
    def eps_surprise(self) -> float | None:
        """EPS beat/miss amount. Positive = beat."""
        if self.eps_actual is not None and self.eps_estimate is not None:
            return self.eps_actual - self.eps_estimate
        return None

    @property
    def eps_surprise_percent(self) -> float | None:
        """EPS surprise as a percentage. Positive = beat."""
        if self.eps_surprise is not None and self.eps_estimate and self.eps_estimate != 0:
            return (self.eps_surprise / abs(self.eps_estimate)) * 100
        return None

    @property
    def did_beat(self) -> bool | None:
        """Whether the company beat EPS estimates."""
        if self.eps_surprise is not None:
            return self.eps_surprise > 0
        return None
