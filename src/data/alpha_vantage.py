"""Alpha Vantage API client.

Provides methods to fetch stock quotes, daily price history,
and technical indicators (RSI, MACD, SMA, Bollinger Bands).

Free tier: 25 API calls per day.
Docs: https://www.alphavantage.co/documentation/
"""

from __future__ import annotations

from datetime import date, datetime

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.data.cache import cache
from src.models.market import OHLCV, MarketOverview, Quote, TechnicalIndicator, SignalStrength
from src.utils.config import get_api_key
from src.utils.logging import get_logger

log = get_logger(__name__)

BASE_URL = "https://www.alphavantage.co/query"

# Cache TTL: 4 hours (covers morning→evening same-day reuse)
CACHE_TTL = 4 * 3600


class AlphaVantageClient:
    """Client for the Alpha Vantage REST API."""

    def __init__(self, api_key: str | None = None):
        """Initialize with an API key.

        Args:
            api_key: Alpha Vantage API key. If None, reads from env.
        """
        self.api_key = api_key or get_api_key("ALPHA_VANTAGE_API_KEY")
        self.client = httpx.Client(timeout=30.0)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def _request(self, params: dict) -> dict:
        """Make a cached, retryable API request.

        Args:
            params: Query parameters for the Alpha Vantage API.

        Returns:
            Parsed JSON response.

        Raises:
            httpx.HTTPStatusError: On HTTP errors.
            ValueError: If the API returns an error message.
        """
        params["apikey"] = self.api_key

        # Check cache
        cache_key = f"av:{params.get('function', '')}:{params.get('symbol', '')}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        log.info("alpha_vantage_request", function=params.get("function"), symbol=params.get("symbol"))
        response = self.client.get(BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()

        # Alpha Vantage returns errors as JSON with "Error Message" or "Note" keys
        if "Error Message" in data:
            raise ValueError(f"Alpha Vantage error: {data['Error Message']}")
        if "Note" in data:
            log.warning("alpha_vantage_rate_limit", note=data["Note"])
            raise ValueError(f"Alpha Vantage rate limit: {data['Note']}")

        cache.set(cache_key, data, ttl=CACHE_TTL)
        return data

    def get_quote(self, ticker: str) -> Quote:
        """Fetch the latest quote for a stock.

        Args:
            ticker: Stock ticker symbol (e.g. AAPL).

        Returns:
            A Quote model with current price, change, volume.
        """
        data = self._request({
            "function": "GLOBAL_QUOTE",
            "symbol": ticker,
        })
        gq = data.get("Global Quote", {})

        return Quote(
            ticker=ticker,
            price=float(gq.get("05. price", 0)),
            change=float(gq.get("09. change", 0)),
            change_percent=float(gq.get("10. change percent", "0%").rstrip("%")),
            volume=int(gq.get("06. volume", 0)),
            high=float(gq.get("03. high", 0)) or None,
            low=float(gq.get("04. low", 0)) or None,
            open=float(gq.get("02. open", 0)) or None,
            previous_close=float(gq.get("08. previous close", 0)) or None,
            timestamp=datetime.now(),
        )

    def get_daily_prices(self, ticker: str, outputsize: str = "compact") -> list[OHLCV]:
        """Fetch daily OHLCV price history.

        Args:
            ticker: Stock ticker symbol.
            outputsize: 'compact' (last 100 days) or 'full' (20+ years).

        Returns:
            List of OHLCV bars, most recent first.
        """
        data = self._request({
            "function": "TIME_SERIES_DAILY",
            "symbol": ticker,
            "outputsize": outputsize,
        })
        time_series = data.get("Time Series (Daily)", {})

        bars = []
        for date_str, values in time_series.items():
            bars.append(OHLCV(
                date=date.fromisoformat(date_str),
                open=float(values["1. open"]),
                high=float(values["2. high"]),
                low=float(values["3. low"]),
                close=float(values["4. close"]),
                volume=int(values["5. volume"]),
            ))

        return sorted(bars, key=lambda b: b.date, reverse=True)

    def get_rsi(self, ticker: str, period: int = 14) -> TechnicalIndicator:
        """Fetch RSI (Relative Strength Index).

        Args:
            ticker: Stock ticker symbol.
            period: RSI lookback period (default 14).

        Returns:
            TechnicalIndicator with RSI value and buy/sell signal.
        """
        data = self._request({
            "function": "RSI",
            "symbol": ticker,
            "interval": "daily",
            "time_period": str(period),
            "series_type": "close",
        })
        analysis = data.get("Technical Analysis: RSI", {})
        if not analysis:
            return TechnicalIndicator(
                ticker=ticker, indicator=f"rsi_{period}", value=50.0,
                signal=SignalStrength.HOLD, detail="No RSI data available",
            )

        latest_date = sorted(analysis.keys(), reverse=True)[0]
        rsi_value = float(analysis[latest_date]["RSI"])

        # Interpret signal
        if rsi_value >= 70:
            signal = SignalStrength.SELL
            detail = f"RSI({period}) = {rsi_value:.1f} — Overbought territory (≥70)"
        elif rsi_value <= 30:
            signal = SignalStrength.BUY
            detail = f"RSI({period}) = {rsi_value:.1f} — Oversold territory (≤30)"
        elif rsi_value >= 60:
            signal = SignalStrength.HOLD
            detail = f"RSI({period}) = {rsi_value:.1f} — Approaching overbought"
        elif rsi_value <= 40:
            signal = SignalStrength.HOLD
            detail = f"RSI({period}) = {rsi_value:.1f} — Approaching oversold"
        else:
            signal = SignalStrength.HOLD
            detail = f"RSI({period}) = {rsi_value:.1f} — Neutral range"

        return TechnicalIndicator(
            ticker=ticker,
            indicator=f"rsi_{period}",
            value=rsi_value,
            signal=signal,
            detail=detail,
        )

    def get_macd(self, ticker: str) -> TechnicalIndicator:
        """Fetch MACD indicator.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            TechnicalIndicator with MACD line, signal, and histogram.
        """
        data = self._request({
            "function": "MACD",
            "symbol": ticker,
            "interval": "daily",
            "series_type": "close",
        })
        analysis = data.get("Technical Analysis: MACD", {})
        if not analysis:
            return TechnicalIndicator(
                ticker=ticker, indicator="macd",
                value={"macd": 0, "signal": 0, "histogram": 0},
                signal=SignalStrength.HOLD, detail="No MACD data available",
            )

        latest_date = sorted(analysis.keys(), reverse=True)[0]
        macd_val = float(analysis[latest_date]["MACD"])
        signal_val = float(analysis[latest_date]["MACD_Signal"])
        hist_val = float(analysis[latest_date]["MACD_Hist"])

        # Interpret: MACD above signal = bullish
        if hist_val > 0 and macd_val > 0:
            signal = SignalStrength.BUY
            detail = f"MACD bullish: histogram={hist_val:.3f}, above signal line"
        elif hist_val < 0 and macd_val < 0:
            signal = SignalStrength.SELL
            detail = f"MACD bearish: histogram={hist_val:.3f}, below signal line"
        elif hist_val > 0:
            signal = SignalStrength.HOLD
            detail = f"MACD turning bullish: histogram={hist_val:.3f}"
        else:
            signal = SignalStrength.HOLD
            detail = f"MACD turning bearish: histogram={hist_val:.3f}"

        return TechnicalIndicator(
            ticker=ticker,
            indicator="macd",
            value={"macd": macd_val, "signal": signal_val, "histogram": hist_val},
            signal=signal,
            detail=detail,
        )

    def get_sma(self, ticker: str, period: int = 50) -> TechnicalIndicator:
        """Fetch Simple Moving Average.

        Args:
            ticker: Stock ticker symbol.
            period: SMA lookback period (e.g. 50, 200).

        Returns:
            TechnicalIndicator with SMA value and trend signal.
        """
        data = self._request({
            "function": "SMA",
            "symbol": ticker,
            "interval": "daily",
            "time_period": str(period),
            "series_type": "close",
        })
        analysis = data.get(f"Technical Analysis: SMA", {})
        if not analysis:
            return TechnicalIndicator(
                ticker=ticker, indicator=f"sma_{period}", value=0.0,
                signal=SignalStrength.HOLD, detail=f"No SMA({period}) data available",
            )

        latest_date = sorted(analysis.keys(), reverse=True)[0]
        sma_value = float(analysis[latest_date]["SMA"])

        # We'll need the current price to interpret — signal will be
        # refined in the technical_analysis node where we have the quote
        return TechnicalIndicator(
            ticker=ticker,
            indicator=f"sma_{period}",
            value=sma_value,
            signal=SignalStrength.HOLD,
            detail=f"SMA({period}) = ${sma_value:.2f}",
        )

    def get_bbands(self, ticker: str, period: int = 20) -> TechnicalIndicator:
        """Fetch Bollinger Bands.

        Args:
            ticker: Stock ticker symbol.
            period: Lookback period (default 20).

        Returns:
            TechnicalIndicator with upper, middle, lower band values.
        """
        data = self._request({
            "function": "BBANDS",
            "symbol": ticker,
            "interval": "daily",
            "time_period": str(period),
            "series_type": "close",
        })
        analysis = data.get("Technical Analysis: BBANDS", {})
        if not analysis:
            return TechnicalIndicator(
                ticker=ticker, indicator="bollinger_bands",
                value={"upper": 0, "middle": 0, "lower": 0},
                signal=SignalStrength.HOLD, detail="No Bollinger Bands data available",
            )

        latest_date = sorted(analysis.keys(), reverse=True)[0]
        upper = float(analysis[latest_date]["Real Upper Band"])
        middle = float(analysis[latest_date]["Real Middle Band"])
        lower = float(analysis[latest_date]["Real Lower Band"])

        return TechnicalIndicator(
            ticker=ticker,
            indicator="bollinger_bands",
            value={"upper": upper, "middle": middle, "lower": lower},
            signal=SignalStrength.HOLD,
            detail=f"BBands: upper=${upper:.2f}, middle=${middle:.2f}, lower=${lower:.2f}",
        )

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()
