#!/usr/bin/env python3
"""Local development runner.

Run this script to test the agent locally without Cloud Run.
Usage:
    python scripts/run_local.py              # Default: morning briefing
    python scripts/run_local.py --evening    # Evening briefing
    python scripts/run_local.py --debug      # With debug logging
"""

from __future__ import annotations

import argparse
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> None:
    """Run the agent locally."""
    parser = argparse.ArgumentParser(description="Stock Portfolio Agent - Local Runner")
    parser.add_argument("--evening", action="store_true", help="Run evening briefing instead of morning")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    # Set run type
    os.environ["RUN_TYPE"] = "evening" if args.evening else "morning"

    # Import and run
    from src.utils.logging import setup_logging
    setup_logging(level="DEBUG" if args.debug else "INFO")

    from src.utils.logging import get_logger
    log = get_logger("run_local")

    run_type = os.environ["RUN_TYPE"]
    log.info("local_run_starting", run_type=run_type)
    print(f"\n🚀 Starting {run_type} briefing...\n")

    from src.main import main as agent_main
    agent_main()

    print("\n✅ Done!\n")


if __name__ == "__main__":
    main()
