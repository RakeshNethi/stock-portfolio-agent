"""Tests for configuration loading."""

from __future__ import annotations

from pathlib import Path

from src.utils.config import load_portfolio, load_settings


class TestConfigLoader:
    """Test suite for YAML config loading."""

    def test_load_portfolio_from_default(self):
        """Test loading portfolio from the real config/portfolio.yaml."""
        portfolio = load_portfolio()
        assert len(portfolio.accounts) > 0
        assert len(portfolio.all_tickers) > 0

    def test_load_portfolio_from_custom_dir(self, config_dir: Path):
        """Test loading portfolio from a custom config directory."""
        portfolio = load_portfolio(config_dir=config_dir)
        assert len(portfolio.accounts) == 1
        assert portfolio.accounts[0].name == "Test Account"
        assert portfolio.all_tickers == ["AAPL", "TSLA"]

    def test_load_settings(self):
        """Test loading settings from the real config/settings.yaml."""
        settings = load_settings()
        assert "llm" in settings
        assert "notifications" in settings
        assert "alerts" in settings

    def test_load_settings_from_custom_dir(self, config_dir: Path):
        """Test loading settings from a custom directory."""
        settings = load_settings(config_dir=config_dir)
        assert settings["llm"]["model"] == "gemini-2.0-flash"
        assert settings["alerts"]["rsi_overbought"] == 70
