"""Finnhub API client for news and sentiment."""

import httpx
from datetime import datetime, timedelta
from typing import Any

from src.utils.config import get_api_key
from src.utils.logging import get_logger

log = get_logger(__name__)

class FinnhubClient:
    """Client for Finnhub API."""
    
    BASE_URL = "https://finnhub.io/api/v1"
    
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or get_api_key("FINNHUB_API_KEY")
        self.client = httpx.Client(timeout=10.0)
        
    def get_company_news(self, tickers: list[str], days: int = 2) -> list[dict[str, Any]]:
        """Fetch recent company news for a list of tickers."""
        if not self.api_key:
            log.warning("finnhub_client_no_api_key")
            return []
            
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        
        all_news = []
        try:
            for ticker in tickers:
                url = f"{self.BASE_URL}/company-news"
                params = {
                    "symbol": ticker,
                    "from": start_str,
                    "to": end_str,
                    "token": self.api_key
                }
                response = self.client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                all_news.extend(data[:5])  # Get top 5 news per ticker
            return all_news
        except Exception as e:
            log.error("finnhub_client_news_error", error=str(e))
            return []
            
    def get_sentiment(self, tickers: list[str]) -> dict[str, float]:
        """Fetch sentiment for a list of tickers."""
        if not self.api_key:
            return {}
            
        sentiment_scores = {}
        try:
            for ticker in tickers:
                url = f"{self.BASE_URL}/news-sentiment"
                params = {
                    "symbol": ticker,
                    "token": self.api_key
                }
                response = self.client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                # Extract buzz/sentiment metric
                if "sentiment" in data and data["sentiment"]:
                    sentiment_scores[ticker] = data["sentiment"].get("bullishPercent", 0.5)
            return sentiment_scores
        except Exception as e:
            log.error("finnhub_client_sentiment_error", error=str(e))
            return {}
