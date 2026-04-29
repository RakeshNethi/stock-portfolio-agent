"""Configuration loader.

Reads YAML config files and environment variables to produce
typed configuration objects used throughout the agent.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from src.models.portfolio import Portfolio

# Default config directory (relative to project root)
_CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"


def _load_yaml(path: Path) -> dict[str, Any]:
    """Load and parse a YAML file."""
    with open(path) as f:
        return yaml.safe_load(f) or {}


def load_portfolio(config_dir: Path | None = None) -> Portfolio:
    """Load portfolio from config/portfolio.yaml.

    Args:
        config_dir: Override path to the config directory.

    Returns:
        A validated Portfolio model.
    """
    config_dir = config_dir or _CONFIG_DIR
    data = _load_yaml(config_dir / "portfolio.yaml")
    return Portfolio(**data)


def load_settings(config_dir: Path | None = None) -> dict[str, Any]:
    """Load agent settings from config/settings.yaml.

    Args:
        config_dir: Override path to the config directory.

    Returns:
        Raw settings dictionary.
    """
    config_dir = config_dir or _CONFIG_DIR
    return _load_yaml(config_dir / "settings.yaml")


def get_api_key(name: str) -> str:
    """Get an API key from environment variables.

    Loads from .env file if present (for local development).
    In production (Cloud Run), secrets are injected as env vars
    via Secret Manager.

    Args:
        name: Environment variable name (e.g. ALPHA_VANTAGE_API_KEY).

    Returns:
        The API key string.

    Raises:
        ValueError: If the key is not set or is a placeholder.
    """
    load_dotenv()
    value = os.environ.get(name, "")
    if not value or value.startswith("your_"):
        raise ValueError(
            f"API key '{name}' is not configured. "
            f"Set it in your .env file or as an environment variable."
        )
    return value


def get_run_type() -> str:
    """Get the current run type (morning or evening).

    Determined by the RUN_TYPE environment variable, set by
    Cloud Scheduler when triggering the Cloud Run Job.

    Returns:
        'morning' or 'evening'. Defaults to 'morning'.
    """
    load_dotenv()
    run_type = os.environ.get("RUN_TYPE", "morning").lower()
    if run_type not in ("morning", "evening"):
        run_type = "morning"
    return run_type
