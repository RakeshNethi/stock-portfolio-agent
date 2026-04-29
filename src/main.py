"""Main entrypoint for the Stock Portfolio Agent.

This module is invoked by Cloud Run Jobs or run locally.
It initializes logging, builds the LangGraph workflow,
and executes a single run (morning or evening briefing).
"""

from __future__ import annotations

import sys

from src.agent.graph import graph
from src.utils.config import get_run_type
from src.utils.logging import get_logger, setup_logging


def main() -> None:
    """Execute a single agent run."""
    setup_logging(level="INFO")
    log = get_logger("main")

    run_type = get_run_type()
    log.info("agent_starting", run_type=run_type)

    try:
        # Initialize state and run the graph
        initial_state = {
            "run_type": run_type,
            "retry_count": 0,
            "upcoming_earnings": [],
            "recent_surprises": [],
            "news_headlines": [],
            "audit_log": [],
        }

        result = graph.invoke(initial_state)

        # Log summary
        briefing = result.get("briefing", {})
        audit_entries = result.get("audit_log", [])
        log.info(
            "agent_complete",
            run_type=run_type,
            has_briefing=bool(briefing),
            audit_entries=len(audit_entries),
            quality_score=result.get("quality_score", 0),
        )

    except Exception as e:
        log.error("agent_failed", error=str(e), exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
