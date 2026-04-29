"""Technical analysis node.

Runs RSI, MACD, SMA, and Bollinger Bands analysis on each
portfolio ticker using Alpha Vantage's built-in indicators,
then interprets the signals relative to current price.
"""

from __future__ import annotations

from datetime import datetime

from src.agent.state import AgentState
from src.data.alpha_vantage import AlphaVantageClient
from src.models.market import SignalStrength, TechnicalIndicator, TechnicalSummary
from src.utils.logging import get_logger

log = get_logger(__name__)


def _interpret_sma_signal(
    price: float, sma_value: float, period: int
) -> tuple[SignalStrength, str]:
    """Interpret SMA relative to current price.

    Args:
        price: Current stock price.
        sma_value: SMA value.
        period: SMA period (e.g. 50, 200).

    Returns:
        Tuple of (signal, detail string).
    """
    if sma_value == 0:
        return SignalStrength.HOLD, f"SMA({period}) data unavailable"

    pct_above = ((price - sma_value) / sma_value) * 100

    if pct_above > 5:
        return SignalStrength.BUY, (
            f"Price ${price:.2f} is {pct_above:.1f}% above SMA({period}) ${sma_value:.2f} — bullish trend"
        )
    elif pct_above < -5:
        return SignalStrength.SELL, (
            f"Price ${price:.2f} is {abs(pct_above):.1f}% below SMA({period}) ${sma_value:.2f} — bearish trend"
        )
    else:
        return SignalStrength.HOLD, (
            f"Price ${price:.2f} near SMA({period}) ${sma_value:.2f} ({pct_above:+.1f}%)"
        )


def _interpret_bbands_signal(
    price: float, bands: dict
) -> tuple[SignalStrength, str]:
    """Interpret Bollinger Bands relative to current price.

    Args:
        price: Current stock price.
        bands: Dict with 'upper', 'middle', 'lower' keys.

    Returns:
        Tuple of (signal, detail string).
    """
    upper = bands.get("upper", 0)
    lower = bands.get("lower", 0)

    if upper == 0 or lower == 0:
        return SignalStrength.HOLD, "Bollinger Bands data unavailable"

    if price >= upper:
        return SignalStrength.SELL, (
            f"Price ${price:.2f} at/above upper band ${upper:.2f} — potentially overbought"
        )
    elif price <= lower:
        return SignalStrength.BUY, (
            f"Price ${price:.2f} at/below lower band ${lower:.2f} — potentially oversold"
        )
    else:
        band_position = (price - lower) / (upper - lower) * 100
        return SignalStrength.HOLD, (
            f"Price at {band_position:.0f}% of Bollinger range (${lower:.2f} — ${upper:.2f})"
        )


def _compute_overall_signal(indicators: list[TechnicalIndicator]) -> SignalStrength:
    """Derive overall signal from individual indicators via simple scoring.

    Args:
        indicators: List of computed technical indicators.

    Returns:
        Aggregate signal strength.
    """
    score_map = {
        SignalStrength.STRONG_BUY: 2,
        SignalStrength.BUY: 1,
        SignalStrength.HOLD: 0,
        SignalStrength.SELL: -1,
        SignalStrength.STRONG_SELL: -2,
    }
    if not indicators:
        return SignalStrength.HOLD

    total = sum(score_map.get(ind.signal, 0) for ind in indicators)
    avg = total / len(indicators)

    if avg >= 1.0:
        return SignalStrength.STRONG_BUY
    elif avg >= 0.4:
        return SignalStrength.BUY
    elif avg <= -1.0:
        return SignalStrength.STRONG_SELL
    elif avg <= -0.4:
        return SignalStrength.SELL
    else:
        return SignalStrength.HOLD


def run_technical_analysis(state: AgentState) -> dict:
    """Run technical indicators on each portfolio ticker.

    This node uses Alpha Vantage's built-in indicator endpoints
    (RSI, MACD, SMA, Bollinger Bands) and interprets them
    relative to the current price from the quotes in state.

    Args:
        state: Agent state with quotes populated.

    Returns:
        State update with technical_signals per ticker.
    """
    # Only analyze holdings we own, not the full watchlist
    # (to conserve API calls on the free tier)
    portfolio = state.get("portfolio", {})
    holding_tickers = set()
    for acct in portfolio.get("accounts", []):
        for h in acct.get("holdings", []):
            holding_tickers.add(h["ticker"])

    quotes = state.get("quotes", {})
    log.info("technical_analysis_start", ticker_count=len(holding_tickers))

    client = AlphaVantageClient()
    technical_signals = {}

    try:
        for ticker in sorted(holding_tickers):
            log.info("analyzing_ticker", ticker=ticker)
            quote_data = quotes.get(ticker, {})
            current_price = quote_data.get("price", 0)

            indicators: list[TechnicalIndicator] = []

            # RSI
            try:
                rsi = client.get_rsi(ticker)
                indicators.append(rsi)
            except Exception as e:
                log.warning("rsi_error", ticker=ticker, error=str(e))

            # MACD
            try:
                macd = client.get_macd(ticker)
                indicators.append(macd)
            except Exception as e:
                log.warning("macd_error", ticker=ticker, error=str(e))

            # SMA 50
            try:
                sma50 = client.get_sma(ticker, period=50)
                if current_price > 0:
                    signal, detail = _interpret_sma_signal(current_price, sma50.value, 50)
                    sma50.signal = signal
                    sma50.detail = detail
                indicators.append(sma50)
            except Exception as e:
                log.warning("sma50_error", ticker=ticker, error=str(e))

            # SMA 200
            try:
                sma200 = client.get_sma(ticker, period=200)
                if current_price > 0:
                    signal, detail = _interpret_sma_signal(current_price, sma200.value, 200)
                    sma200.signal = signal
                    sma200.detail = detail
                indicators.append(sma200)
            except Exception as e:
                log.warning("sma200_error", ticker=ticker, error=str(e))

            # Bollinger Bands
            try:
                bbands = client.get_bbands(ticker)
                if current_price > 0 and isinstance(bbands.value, dict):
                    signal, detail = _interpret_bbands_signal(current_price, bbands.value)
                    bbands.signal = signal
                    bbands.detail = detail
                indicators.append(bbands)
            except Exception as e:
                log.warning("bbands_error", ticker=ticker, error=str(e))

            # Compute overall signal
            overall = _compute_overall_signal(indicators)
            summary = TechnicalSummary(
                ticker=ticker,
                indicators=indicators,
                overall_signal=overall,
                summary=f"{ticker}: {overall.value.upper()} based on {len(indicators)} indicators",
            )
            technical_signals[ticker] = summary.model_dump()

            log.info(
                "ticker_analysis_complete",
                ticker=ticker,
                overall_signal=overall.value,
                indicator_count=len(indicators),
            )

    finally:
        client.close()

    log.info("technical_analysis_complete", tickers_analyzed=len(technical_signals))

    return {
        "technical_signals": technical_signals,
        "audit_log": [
            {
                "timestamp": datetime.now().isoformat(),
                "agent": "TechnicalAnalyzer",
                "action": "run_technical_analysis",
                "detail": f"Analyzed {len(technical_signals)} tickers",
            }
        ],
    }
