"""Financial Modeling Prep API client for earnings and fundamentals."""

import httpx
from datetime import datetime, timedelta
from typing import Any

from src.utils.config import get_api_key
from src.utils.logging import get_logger

log = get_logger(__name__)

class FMPClient:
    """Client for Financial Modeling Prep API."""
    
    BASE_URL = "https://financialmodelingprep.com/api/v3"
    
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or get_api_key("FMP_API_KEY")
        self.client = httpx.Client(timeout=10.0)
        
    def get_earnings_calendar(self, tickers: list[str], lookahead_days: int = 7) -> list[dict[str, Any]]:
        """Fetch upcoming earnings calendar."""
        if not self.api_key:
            log.warning("fmp_client_no_api_key")
            return []
            
        start_date = datetime.now()
        end_date = start_date + timedelta(days=lookahead_days)
        
        try:
            url = f"{self.BASE_URL}/earning_calendar"
            params = {
                "apikey": self.api_key,
                "from": start_date.strftime("%Y-%m-%d"),
                "to": end_date.strftime("%Y-%m-%d")
            }
            response = self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Filter for requested tickers
            ticker_set = set(tickers)
            upcoming = [item for item in data if item.get("symbol") in ticker_set]
            return upcoming
        except Exception as e:
            log.error("fmp_client_earnings_error", error=str(e))
            return []
            
    def get_recent_surprises(self, tickers: list[str], lookback_days: int = 7) -> list[dict[str, Any]]:
        """Fetch recent earnings surprises."""
        if not self.api_key:
            return []
            
        surprises = []
        try:
            for ticker in tickers:
                url = f"{self.BASE_URL}/earnings-surprises/{ticker}"
                response = self.client.get(url, params={"apikey": self.api_key})
                response.raise_for_status()
                data = response.json()
                
                if data:
                    # Filter based on date if needed, or just take the most recent
                    surprises.append(data[0])
            return surprises
        except Exception as e:
            log.error("fmp_client_surprises_error", error=str(e))
            return []
