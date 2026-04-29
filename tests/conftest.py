"""Shared test fixtures and configuration."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

# Ensure we use test-safe config
os.environ.setdefault("ALPHA_VANTAGE_API_KEY", "test_key")
os.environ.setdefault("GEMINI_API_KEY", "test_key")
os.environ.setdefault("RUN_TYPE", "morning")


@pytest.fixture
def sample_portfolio_data() -> dict:
    """Sample portfolio data matching config/portfolio.yaml structure."""
    return {
        "accounts": [
            {
                "name": "Test Brokerage",
                "broker": "test",
                "holdings": [
                    {"ticker": "AAPL", "shares": 50, "cost_basis": 178.25},
                    {"ticker": "NVDA", "shares": 30, "cost_basis": 485.50},
                ],
            }
        ],
        "watchlist": ["TSLA", "AMD"],
    }


@pytest.fixture
def sample_quotes() -> dict:
    """Sample quote data for testing."""
    return {
        "AAPL": {
            "ticker": "AAPL",
            "price": 198.50,
            "change": 1.25,
            "change_percent": 0.63,
            "volume": 45000000,
        },
        "NVDA": {
            "ticker": "NVDA",
            "price": 892.00,
            "change": 28.50,
            "change_percent": 3.30,
            "volume": 62000000,
        },
    }


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    """Create a temporary config directory with test configs."""
    config = tmp_path / "config"
    config.mkdir()

    portfolio_yaml = config / "portfolio.yaml"
    portfolio_yaml.write_text("""
accounts:
  - name: Test Account
    broker: test
    holdings:
      - ticker: AAPL
        shares: 10
        cost_basis: 150.00
watchlist:
  - TSLA
""")

    settings_yaml = config / "settings.yaml"
    settings_yaml.write_text("""
llm:
  model: gemini-2.0-flash
  temperature: 0.3
notifications:
  email:
    enabled: false
  telegram:
    enabled: false
alerts:
  rsi_overbought: 70
  rsi_oversold: 30
""")

    return config
